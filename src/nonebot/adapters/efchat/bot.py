import json
import re
from typing import Union, Optional
from nonebot.adapters import Bot as BaseBot
from nonebot.message import handle_event
from .event import MessageEvent, WhisperMessageEvent, ChannelMessageEvent, Event
from .message import Message, MessageSegment
from .log import log
from .models import EFChatBotConfig

class Bot(BaseBot):
    """Bot 只负责消息和事件处理，WebSocket 由 Adapter 统一管理"""

    def __init__(self, adapter: "Adapter", bot_config: "EFChatBotConfig"):
        super().__init__(adapter, f"{bot_config.nick}@{bot_config.channel}")
        self.adapter: Adapter = adapter
        self.nick = bot_config.nick
        self.channel = bot_config.channel
        self.head = bot_config.head
        self.ws: Optional[any] = None
        self.password = bot_config.password
        self.token = bot_config.token

    @property
    def bot_id(self) -> str:
        return f"{self.nick}@{self.channel}"

    async def start(self):
        """调用适配器进行连接"""
        await self.adapter._forward_ws(self)

    async def send(self, event: MessageEvent, message: Union[str, Message, MessageSegment], **kwargs):
        """根据事件类型选择发送方式"""
        if isinstance(event, WhisperMessageEvent):
            await self.send_whisper_message(event, message, **kwargs)
        elif isinstance(event, ChannelMessageEvent):
            await self.send_chat_message(event, message, **kwargs)

    async def send_chat_message(self, event: ChannelMessageEvent, message: Union[str, Message, MessageSegment], show: bool = True, at_sender: bool = False, reply_message: bool = False):
        """发送房间消息，并格式化 @用户 和 回复原消息"""
        formatted_message = self._format_send_message(event, message, at_sender, reply_message)
        await self.call_api("chat", text=str(formatted_message), show=("1" if show else "0"), head=self.head)

    async def send_whisper_message(self, event: WhisperMessageEvent, message: Union[str, Message, MessageSegment], at_sender: bool = False, reply_message: bool = False):
        """发送私聊消息，并格式化 @用户 和 回复原消息"""
        formatted_message = self._format_send_message(event, message, at_sender, reply_message)
        await self.call_api("whisper", nick=event.nick, text=str(formatted_message))

    async def move(self, new_channel: str):
        """移动到新房间"""
        old_id = self.bot_id
        await self.call_api("move", channel=new_channel)
        self.channel = new_channel
        new_id = self.bot_id
        await self.adapter.rename_bot(old_id, new_id)

    async def change_nick(self, new_nick: str):
        """修改昵称"""
        old_id = self.bot_id
        await self.call_api("changenick", nick=new_nick)
        self.nick = new_nick
        new_id = self.bot_id
        await self.adapter.rename_bot(old_id, new_id)

    async def get_chat_history(self, num: int):
        """获取历史消息"""
        await self.call_api("get_old", num=num)

    async def call_api(self, api: str, **kwargs):
        """调用适配器的 API 统一管理方法"""
        await self.adapter._call_api(self, api, **kwargs)

    async def send_packet(self, data: dict):
        """发送数据包"""
        if self.ws:
            await self.ws.send(json.dumps(data))

    async def handle_event(self, event: Event) -> None:
        """处理收到的事件"""
        if isinstance(event, MessageEvent):
            self._check_at_me(event)
            self._check_nickname(event)

        await handle_event(self, event)

    def _format_send_message(self, event: MessageEvent, message: Union[str, Message, MessageSegment], at_sender: bool, reply_message: bool) -> Message:
        """格式化消息，添加 @用户 和 回复原消息"""
        full_message = Message()
        
        if reply_message:
            full_message += MessageSegment.text(f"> {event.trip} {event.nick}:\n> {event.get_message()}\n")

        if at_sender and event.nick:
            full_message += MessageSegment.at(event.nick) + " "

        full_message += message
        return full_message

    def _check_at_me(self, event: MessageEvent) -> None:
        """检查消息是否 @机器人，去除并设置 `event.to_me`"""
        if not isinstance(event, MessageEvent) or not event.message:
            return

        if event.message_type == "whisper":
            event.to_me = True
            return

        if event.message[0].type == "at" and str(event.message[0].data.get("target", "")) == self.nick:
            event.to_me = True
            event.message.pop(0)
            if event.message and event.message[0].type == "text":
                event.message[0].data["text"] = event.message[0].data["text"].lstrip()
                if not event.message[0].data["text"]:
                    del event.message[0]

    def _check_nickname(self, event: MessageEvent) -> None:
        """检查消息是否包含机器人昵称，去除并设置 `event.to_me`"""
        if not event.message or event.message[0].type != "text":
            return

        first_text = event.message[0].data["text"]
        if re.search(rf"^({re.escape(self.nick)})([\s,，]*|$)", first_text, re.IGNORECASE):
            log("DEBUG", f"Bot {self.bot_id} 被用户提及")
            event.to_me = True
            event.message[0].data["text"] = first_text[len(self.nick):].lstrip()