from nonebot.adapters import MessageSegment as BaseMessageSegment, Message as BaseMessage
from typing import Type, Union
from typing_extensions import Self
from collections.abc import Iterable
from pathlib import Path
import re


class MessageSegment(BaseMessageSegment["Message"]):
    """基础消息段类，提供静态方法构建不同类型的消息"""

    @staticmethod
    def text(text: str) -> "Text":
        return Text("text", {"text": text})

    @staticmethod
    def image(url: str) -> "Image":
        return Image("image", {"url": url})

    @staticmethod
    def at(target: str) -> "At":
        return At("at", {"target": target})

    @staticmethod
    def voice(
        url: str = None, path: Union[str, Path] = None, raw: bytes = None, src_name: str = None
    ) -> "Voice":
        """
        生成语音消息段，支持：
        - `url` 语音文件 URL
        - `path` 本地文件路径（支持 `str` 和 `Path`）
        - `raw` 语音 `bytes` 数据
        - `src_name` 资源名称
        """

        provided_args = sum(bool(arg) for arg in [url, path, raw, src_name])
        if provided_args == 0:
            raise ValueError("必须提供一个参数 (url, path, raw 或 src_name)，不能全部为空")
        elif provided_args > 1:
            raise ValueError("只能提供一个参数 (url, path, raw 或 src_name)，不能同时填充多个")

        if url and re.match(r"https://efchat\.melon\.fish/oss/(.+)", url):
            extracted_src_name = re.search(r"https://efchat\.melon\.fish/oss/(.+)", url).group(1)
            return Voice("voice", {"src": f"USERSENDVOICE_{extracted_src_name}", "url": f"https://efchat.melon.fish/oss/{extracted_src_name}"})

        if src_name is not None:
            src_name = src_name.lstrip("USERSENDVOICE_")
            return Voice("voice", {"src": f"USERSENDVOICE_{src_name}", "url": f"https://efchat.melon.fish/oss/{src_name}"})

        return Voice("voice", {"path": str(path) if path else None, "raw": raw, "requires_upload": True})

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


class Voice(MessageSegment):
    """语音消息段"""

    def __str__(self) -> str:
        return self.data.get("src", "")

class Text(MessageSegment):
    """文本消息段"""

    def __str__(self) -> str:
        return self.data["text"]


class Image(MessageSegment):
    """图片消息段"""

    def __str__(self) -> str:
        return f"![image]({self.data['url']})"


class At(MessageSegment):
    """@ 用户消息段"""

    def __str__(self) -> str:
        return f"@{self.data['target']}"


class Message(BaseMessage[MessageSegment]):
    """消息类，继承 BaseMessage 并扩展文本解析和合并"""

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
        """提取纯文本"""
        return "".join(seg.data["text"] for seg in self if seg.is_text())

    def reduce(self) -> None:
        """合并消息内连续的纯文本段"""
        index = 1
        while index < len(self):
            if self[index - 1].type == "text" and self[index].type == "text":
                self[index - 1].data["text"] += self[index].data["text"]
                del self[index]
            else:
                index += 1

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
                segments.append(MessageSegment.voice(src_name=voice_src))
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
