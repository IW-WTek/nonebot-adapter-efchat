import re
from typing import TYPE_CHECKING, Union
from nonebot.adapters import Bot as BaseBot
from nonebot.message import handle_event
from nonebot.matcher import current_event
from .models import EFChatBotConfig
from .event import Event, ChannelMessageEvent, WhisperMessageEvent, MessageEvent
from .message import Message, MessageSegment
from .utils import logger, upload_voice

if TYPE_CHECKING:
    from .adapter import Adapter


def _format_send_message(
    message: Union[str, Message, MessageSegment],
    at_sender: bool,
    reply_message: bool,
) -> Message:
    """格式化消息，添加 @用户 和 回复原消息"""
    full_message = Message()
    event = current_event.get()
    assert isinstance(event, MessageEvent)

    if reply_message:
        full_message += MessageSegment.text(
            f"> {event.trip} {event.nick}:\n> {event.get_message()}\n\n"
        )

    if at_sender and event.nick:
        full_message += f"{MessageSegment.at(event.nick)} "

    full_message += message
    return full_message


class Bot(BaseBot):
    def __init__(self, adapter: "Adapter", self_id: str, cfg: EFChatBotConfig):
        super().__init__(adapter, self_id)
        self.cfg = cfg

    async def send(
        self,
        event: MessageEvent,
        message: Union[str, Message, MessageSegment],
        at_sender: bool = False,
        reply_message: bool = False,
    ):
        """自适应发送消息"""

        voice_segment = None

        def target_method(event: MessageEvent, **kwargs):
            if isinstance(event, ChannelMessageEvent):
                return self.send_chat_message(**kwargs)
            if isinstance(event, WhisperMessageEvent):
                return self.send_whisper_message(**kwargs)
            raise ValueError(f"Unsupported MessageEvent type: {type(event)}")

        if isinstance(message, Message):
            for segment in message:
                if segment.type == "voice":
                    voice_segment = segment
                    break

        elif isinstance(message, MessageSegment) and message.type == "voice":
            voice_segment = message

        if voice_segment and voice_segment.data.get("requires_upload"):
            src_name = await upload_voice(
                self.adapter,
                voice_segment.data.get("url"),
                voice_segment.data.get("path"),
                voice_segment.data.get("raw"),
            )
            voice_segment = MessageSegment.voice(src_name=src_name)

        if voice_segment:
            await target_method(event, voice_segment=voice_segment)
        else:
            await target_method(
                event, message=message, at_sender=at_sender, reply_message=reply_message
            )

    async def send_chat_message(
        self,
        message: Union[str, Message, MessageSegment],
        show: bool = False,
    ):
        """发送房间消息，并格式化 @用户 和 回复原消息"""
        await self.call_api(
            "chat",
            text=str(message),
            show=("1" if show else "0"),
            head=self.cfg.head,
        )

    async def send_whisper_message(
        self,
        message: Union[str, Message, MessageSegment],
    ):
        """发送私聊消息(因为服务器上的某个尚未发现的bug，此消息不会显示给用户)"""
        event = current_event.get()
        assert isinstance(event, MessageEvent)
        await self.call_api("whisper", nick=event.nick, text=str(message))

    async def move(self, new_channel: str):
        """移动到指定房间"""
        await self.call_api("move", channel=new_channel)
        self.cfg.channel = new_channel

    async def change_nick(self, new_nick: str):
        """修改机器人名称"""
        await self.call_api("changenick", nick=new_nick)
        self.cfg.nick = new_nick

    async def get_chat_history(self, num: int):
        """获取历史聊天记录"""
        await self.call_api("get_old", num=num)

    async def handle_event(self, event: Event) -> None:
        """处理收到的事件"""
        if not (
            isinstance(event, (ChannelMessageEvent, WhisperMessageEvent))
            and self.cfg.ignore_self
            and event.nick == self.cfg.nick
        ):
            if isinstance(event, MessageEvent):
                _check_at_me(self, event)
                _check_nickname(self, event)

            await handle_event(self, event)
        else:
            logger.debug(
                f"EFChat {self.self_id} | 过滤自身消息: {event.get_plaintext()}"
            )


def _check_at_me(bot, event: MessageEvent) -> None:
    """检查消息开头或结尾是否存在 @机器人，去除并赋值 `event.to_me`"""
    if not isinstance(event, MessageEvent) or not event.message:
        return

    if event.message_type == "whisper":
        event.to_me = True
        return

    def _is_at_me_seg(segment: MessageSegment):
        return segment.type == "at" and str(segment.data.get("target", "")) == str(
            bot.self_id
        )

    if _is_at_me_seg(event.message[0]):
        event.to_me = True
        event.message.pop(0)
        if event.message and event.message[0].type == "text":
            event.message[0].data["text"] = event.message[0].data["text"].lstrip()
            if not event.message[0].data["text"]:
                del event.message[0]

    if not event.to_me:
        i = -1
        last_msg_seg = event.message[i]
        if (
            last_msg_seg.type == "text"
            and not last_msg_seg.data["text"].strip()
            and len(event.message) >= 2
        ):
            i -= 1
            last_msg_seg = event.message[i]

        if _is_at_me_seg(last_msg_seg):
            event.to_me = True
            del event.message[i:]

    if not event.message:
        event.message.append(MessageSegment.text(""))


def _check_nickname(bot: "Bot", event: MessageEvent) -> None:
    """检查消息开头是否存在昵称，去除并赋值 `event.to_me`"""
    first_msg_seg = event.message[0]
    if first_msg_seg.type != "text":
        return

    nicknames = {re.escape(bot.cfg.nick)}
    if not nicknames:
        return

    nickname_regex = "|".join(nicknames)
    first_text = first_msg_seg.data["text"]
    if m := re.search(rf"^({nickname_regex})([\s,，]*|$)", first_text, re.IGNORECASE):
        logger.debug(f"被用户at: {m[1]}")
        event.to_me = True
        first_msg_seg.data["text"] = first_text[m.end() :]
