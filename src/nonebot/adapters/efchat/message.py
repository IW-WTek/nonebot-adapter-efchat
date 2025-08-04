import base64
import imghdr
from nonebot.adapters import (
    MessageSegment as BaseMessageSegment,
    Message as BaseMessage,
)
from typing import Type, Union, Optional
from typing_extensions import Self
from collections.abc import Iterable
from pathlib import Path
import re

_VOICE_URL_RE = re.compile(r"https://efchat\.melon\.fish/oss/(.+)")


class MessageSegment(BaseMessageSegment["Message"]):
    """基础消息段类，提供静态方法构建不同类型的消息"""

    @staticmethod
    def text(text: str) -> "Text":
        return Text("text", {"text": text})

    @staticmethod
    def image(
        url: Optional[str] = None,
        raw: Optional[bytes] = None,
        path: Optional[Union[str, Path]] = None,
    ) -> "Image":
        if url:
            return Image("image", {"url": url})

        if raw is not None:
            image_type = imghdr.what(None, raw) or "png"
            data_url = MessageSegment._create_data_url(raw, f"image/{image_type}")
            return Image("image", {"url": data_url})

        if path:
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                image_type = imghdr.what(None, raw) or "png"
                data_url = MessageSegment._create_data_url(raw, f"image/{image_type}")
                return Image("image", {"url": data_url})
            except (IOError, OSError) as e:
                raise ValueError(f"无法读取文件 {path}: {str(e)}") from e

        raise ValueError("Must provide at least one of url, raw, or path")

    @staticmethod
    def at(target: str) -> "At":
        return At("at", {"target": target})

    @staticmethod
    def voice(
        url: Optional[str] = None,
        path: Optional[Union[str, Path]] = None,
        raw: Optional[bytes] = None,
        src_name: Optional[str] = None,
    ) -> "Voice":
        """
        语音消息段

        以下参数一次只能填一个
        Args:
        - url (str): 语音文件的网络地址
        - path (str|Path): 语音文件路径
        - raw (bytes): 语音数据
        - src_name (str): oss资源
        """
        provided = sum(bool(x) for x in (url, path, raw, src_name))
        if provided == 0 or provided > 1:
            raise ValueError("必须且只能提供一个参数 url, path, raw, src_name")

        if url and (m := _VOICE_URL_RE.match(url)):
            return MessageSegment._voice_from_src(m[1])

        if src_name is not None:
            return MessageSegment._voice_from_src(src_name)

        return MessageSegment._voice_upload(url, path, raw)

    @staticmethod
    def _voice_from_src(src_name: str) -> "Voice":
        clean = src_name.removeprefix("USERSENDVOICE_")
        return Voice(
            "voice",
            {
                "src": f"USERSENDVOICE_{clean}",
                "url": f"https://efchat.melon.fish/oss/{clean}",
            },
        )

    @staticmethod
    def _voice_upload(
        url: Optional[str], path: Optional[Union[str, Path]], raw: Optional[bytes]
    ) -> "Voice":
        return Voice(
            "voice",
            {
                "url": url,
                "path": str(path) if path else None,
                "raw": raw,
                "requires_upload": True,
            },
        )

    @staticmethod
    def _create_data_url(data: bytes, mime_type: str = "image/png") -> str:
        return f"data:{mime_type};base64,{base64.b64encode(data).decode('utf-8')}"

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

    _PARSE_RULES = [
        # (predicate, handler)
        (lambda txt: txt.startswith("!["), lambda txt: _parse_image(txt)),
        (lambda txt: txt.startswith("USERSENDVOICE_"), lambda txt: _parse_voice(txt)),
        (lambda txt: txt.startswith("@"), lambda txt: _parse_at(txt)),
    ]

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
        segs, i = [], 0
        while i < len(msg):
            for pred, handler in Message._PARSE_RULES:
                tail = msg[i:]
                if pred(tail):
                    seg, inc = handler(tail)
                    segs.append(seg)
                    i += inc
                    break
            else:
                segs.append(MessageSegment.text(msg[i:]))
                break
        return segs


# voice: 格式 USERSENDVOICE_static/xxx
def _parse_voice(txt: str) -> tuple[MessageSegment, int]:
    end = txt.find(" ") if " " in txt else len(txt)
    src = txt[:end].replace("static/", "")
    return MessageSegment.voice(src_name=src), end


# image: 格式 ![image](url)
def _parse_image(txt: str) -> tuple[MessageSegment, int]:
    # 找到第一个 '(' 和对应的 ')'
    start = txt.find("(")
    end = txt.find(")", start + 1)
    if start == -1 or end == -1:
        # 解析失败，fallback 到 text
        return MessageSegment.text(txt), len(txt)
    url = txt[start + 1 : end]
    seg = MessageSegment.image(url)
    # consumed = '![image]('  + url + ')'
    return seg, end + 1


# at: 以 '@' 开头，直到空格或字符串末尾
def _parse_at(txt: str) -> tuple[MessageSegment, int]:
    # 如果有空格，就取第一个空格前的所有字符，否则取整条
    end = txt.find(" ") if " " in txt else len(txt)
    target = txt[1:end]
    seg = MessageSegment.at(target)
    return seg, end
