from typing import Type, Union
from typing_extensions import Self
from collections.abc import Iterable
from nonebot.adapters import (
    Message as BaseMessage,
    MessageSegment as BaseMessageSegment,
)


class MessageSegment(BaseMessageSegment["Message"]):
    def __str__(self) -> str:
        if self.type == "image":
            return f"![image]({self.url})"
        elif self.type == "at":
            return f"@{self.data['target']}"
        elif self.type == "voice":
            return "[语音]"
        else:
            return self.data["text"]

    def __add__(
        self, other: Union[str, "MessageSegment", Iterable["MessageSegment"]]
    ) -> "Message":
        return Message(self) + (
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    def __radd__(
        self, other: Union[str, "MessageSegment", Iterable["MessageSegment"]]
    ) -> "Message":
        return (
            MessageSegment.text(other) if isinstance(other, str) else Message(other)
        ) + self

    @classmethod
    def get_message_class(cls) -> Type["Message"]:
        return Message

    def is_text(self) -> bool:
        return self.type == "text"

    @classmethod
    def text(cls, content: str) -> "MessageSegment":
        return cls("text", {"text":content})

    @classmethod
    def image(cls, url: str) -> "MessageSegment":
        return cls("image", {"url": url})

    @classmethod
    def at(cls, target: str) -> "MessageSegment":
        return cls("at", {"target": target})

    @classmethod
    def voice(cls, src: str) -> "MessageSegment":
        """此消息段不可用于发送语音，仅用于解析语音消息"""
        return cls("voice", {"src": f"https://efchat.melon.fish/oss/{src}"})


class Message(BaseMessage[MessageSegment]):

    @classmethod
    def get_segment_class(cls) -> Type[MessageSegment]:
        return MessageSegment

    def __add__(
        self, other: Union[str, MessageSegment, Iterable[MessageSegment]]
    ) -> Self:
        return super().__add__(
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    def __radd__(
        self, other: Union[str, MessageSegment, Iterable[MessageSegment]]
    ) -> Self:
        return super().__radd__(
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    def __iadd__(
        self, other: Union[str, MessageSegment, Iterable[MessageSegment]]
    ) -> Self:
        return super().__iadd__(
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    def extract_plain_text(self) -> str:
        return "".join(seg.data["text"] for seg in self if seg.is_text())

    @staticmethod
    def _construct(msg: str) -> Iterable[MessageSegment]:
        segments = []
        index = 0

        while index < len(msg):
            # 解析图片
            if msg[index:].startswith("![") and "](" in msg[index:]:
                start_index = index + 2
                alt_text_end = msg.find("](", start_index)
                url_start = alt_text_end + 2
                url_end = msg.find(")", url_start)

                if alt_text_end != -1 and url_start != -1 and url_end != -1:
                    url = msg[url_start:url_end]
                    segments.append(MessageSegment.image(url))
                    index = url_end + 1
                    continue

            # 解析语音
            elif msg[index:].startswith("USERSENDVOICE_"):
                end_index = msg.find(" ", index)
                if end_index == -1:
                    end_index = len(msg)

                voice_src = msg[index:end_index]
                voice_src.replace("static/", "")
                segments.append(MessageSegment.voice(voice_src))
                index = end_index
                continue

            # 解析 @
            elif msg[index] == "@":
                end_index = msg.find(" ", index)
                if end_index == -1:
                    end_index = len(msg)
                target = msg[index + 1 : end_index]
                segments.append(MessageSegment.at(target))
                index = end_index
                continue

            # 默认纯文本
            else:
                segments.append(MessageSegment.text(msg[index:]))
                break

        return segments

    def reduce(self) -> None:
        """合并消息内连续的纯文本段。"""
        index = 1
        while index < len(self):
            if self[index - 1].type == "text" and self[index].type == "text":
                self[index - 1].data["text"] += self[index].data["text"]
                del self[index]
            else:
                index += 1
