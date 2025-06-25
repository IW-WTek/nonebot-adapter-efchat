from typing import TYPE_CHECKING, ClassVar, Literal, TypeVar
from copy import deepcopy
from datetime import datetime
from nonebot.adapters import Event as BaseEvent
from nonebot.compat import model_dump, model_validator, PYDANTIC_V2, ConfigDict
from nonebot.compat import type_validate_python
from .message import Message
from .utils import sanitize
from .models import ChatHistory, OnlineUser


class Event(BaseEvent):
    """通用事件"""

    cmd: str
    """原始事件"""
    __cmd__: ClassVar[str] = "unknown"
    event_type: str
    time: int
    """时间"""
    if TYPE_CHECKING:
        to_me: bool

    if PYDANTIC_V2:

        model_config: ConfigDict = ConfigDict(
            extra="allow",  # type: ignore
            arbitrary_types_allowed=True,  # type: ignore
            json_encoders={datetime: lambda dt: int(dt.timestamp())},  # type: ignore
        )
    else:

        class Config:
            extra = "allow"
            arbitrary_types_allowed = True
            copy_on_model_validation = "none"
            json_encoders = {
                datetime: lambda dt: int(dt.timestamp()),
            }

    def get_type(self) -> str:
        return self.event_type

    def get_event_name(self) -> str:
        return self.cmd

    def get_user_id(self) -> str:
        raise ValueError("This event does not have a user_id")

    def get_session_id(self) -> str:
        raise ValueError("This event does not have a session_id")

    def get_message(self) -> "Message":
        raise ValueError("This event does not have a message")

    def get_event_description(self) -> str:
        return sanitize(str(model_dump(self)))

    def get_plaintext(self) -> str:
        return "".join(str(seg) for seg in msg) if (msg := self.get_message()) else ""

    def is_tome(self) -> bool:
        return self.to_me


EVENT_CLASSES: dict[str, type[Event]] = {}

E = TypeVar("E", bound="Event")


def register_event_class(event_class: type[E]) -> type[E]:

    __cmd__ = event_class.__cmd__.split("|")

    for value in __cmd__:
        EVENT_CLASSES[value] = event_class
    return event_class


@register_event_class
class MessageEvent(Event):
    """消息事件"""

    __cmd__: ClassVar[str] = "chat"
    event_type: str = "message"
    isbot: bool = False
    """是否机器人"""
    nick: str
    """发送者昵称"""
    trip: str = ""
    """加密身份标识"""
    to_me: bool = False
    message_type: ClassVar[Literal["channel", "whisper", "html"]]

    if TYPE_CHECKING:
        message: Message
        original_message: Message
        message_id: None = None
        """消息ID"""
        reply: None = None
        """不支持获取引用消息"""

    @model_validator(mode="before")
    def handle_message(cls, values):
        if isinstance(values, dict):
            segments = values.get("msg") if "msg" in values else values.get("text")
            values["message"] = Message(segments)
            values["original_message"] = deepcopy(values["message"])
        return values

    def get_event_name(self) -> str:
        return f"{self.event_type}.{self.message_type}"

    def get_message(self) -> Message:
        return self.message

    def get_user_id(self) -> str:
        return self.nick

    def is_tome(self) -> bool:
        return self.to_me

    def convert(self, data: dict) -> "MessageEvent":
        if data.get("type") == "whisper" and data.get("from") is not None:
            cls = WhisperMessageEvent
        else:
            cls = ChannelMessageEvent
        return type_validate_python(cls, model_dump(self))


class ChannelMessageEvent(MessageEvent):
    """房间消息事件"""

    message_type: str = "channel"
    head: str
    """用户头像链接"""
    level: int
    """等级"""
    channel: str = ""
    """房间名称"""
    mod: bool = False
    """是否受信用户"""

    def get_event_description(self) -> str:
        return sanitize(
            f"Chaneel Message from {self.nick}@[trip: {self.trip}]: {self.message}"
        )

    def get_session_id(self) -> str:
        return f"channel_{self.nick}"


class WhisperMessageEvent(MessageEvent):
    """私聊事件"""

    message_type: str = "whisper"
    text: str
    """提示内容"""

    @model_validator(mode="before")
    def handle_message(cls, values):
        values = super().handle_message(values)
        if isinstance(values, dict):
            values["nick"] = values["from"]
        return values

    def get_event_description(self) -> str:
        return sanitize(
            f"Whisper Message from {self.nick}@[trip: {self.trip}]: {self.message}"
        )

    def get_session_id(self) -> str:
        return f"whisper_{self.nick}"


@register_event_class
class HTMLMessageEvent(MessageEvent):
    """HTML消息事件"""

    __cmd__: ClassVar[str] = "html"
    message_type: str = "html"
    mod: bool = False
    """来自受信用户"""
    admin: bool = False
    """来自管理员"""

    def get_session_id(self) -> str:
        return f"whisper_{self.nick}"

    def get_event_description(self) -> str:
        return sanitize(f"HTML Message from {self.nick}: {self.message}")


class NoticeEvent(Event):
    """通知事件"""

    event_type: str = "notice"
    type: str = ""
    """具体子事件"""

    @model_validator(mode="before")
    def handle_message(cls, values):
        if isinstance(values, dict):
            values["type"] = values["cmd"]
        return values

    def get_event_name(self) -> str:
        return f"{self.event_type}.{self.type}"


class RequestEvent(Event):
    """请求事件"""

    event_type: str = "request"
    text: str
    """事件内容"""
    type: str
    """具体子事件"""

    def get_event_name(self) -> str:
        return f"{self.event_type}.{self.type}"

    def get_event_description(self) -> str:
        return sanitize(f"Received {self.type} from {self.get_user_id()}: {self.text}")


@register_event_class
class SystemNoticeEvent(NoticeEvent):
    """系统通知事件"""

    __cmd__: ClassVar[str] = "info|warn"
    text: str
    """事件内容"""

    def get_event_description(self) -> str:
        return sanitize(f"Received notice {self.type.upper()}: {self.text}")


@register_event_class
class InviteEvent(RequestEvent):
    """邀请事件"""

    __cmd__: ClassVar[str] = "invite"
    to: str
    """邀请到的房间"""
    nick: str
    """邀请人"""

    @model_validator(mode="before")
    def handle_message(cls, values):
        if isinstance(values, dict):
            values["nick"] = values["from"]
        return values


@register_event_class
class JoinRoomEvent(NoticeEvent):
    """加入房间事件"""

    __cmd__: ClassVar[str] = "onlineAdd"
    city: str
    """地理位置"""
    client: str
    """客户端信息"""
    hash: str
    """账号hash"""
    isbot: bool
    """是否机器人"""
    level: int
    """等级"""
    nick: str
    """用户名"""
    trip: str
    """加密身份标识"""
    userid: int
    """用户ID"""
    utype: str = ""
    """用户组(在个别情况下为空)"""

    def get_event_description(self) -> str:
        return sanitize(
            f"User {self.nick}@[trip:{self.trip}] from {self.city} joined the room"
        )


@register_event_class
class LeaveRoomEvent(NoticeEvent):
    """离开房间事件"""

    __cmd__: ClassVar[str] = "onlineRemove"
    nick: str
    """用户名"""

    def get_event_description(self) -> str:
        return sanitize(f"User {self.nick} left the room")


@register_event_class
class OnlineSetEvent(NoticeEvent):
    """在线人数事件"""

    __cmd__: ClassVar[str] = "onlineSet"
    nicks: list[str]
    """在线用户列表"""
    users: list[OnlineUser]
    """用户详细信息列表"""

    def get_event_description(self) -> str:
        return f"当前房间内共有 {len(self.nicks)} 名用户在线"


@register_event_class
class KillEvent(NoticeEvent):
    """封禁事件"""

    __cmd__: ClassVar[str] = "kill|unkill"
    nick: str
    """被封禁用户名称"""

    @model_validator(mode="before")
    def handle_message(cls, values):
        values = super().handle_message(values)
        if isinstance(values, dict):
            values["type"] = values["cmd"]
        return values

    def get_event_description(self) -> str:
        return sanitize(f"User {self.nick} has been {self.type}.")


@register_event_class
class ShoutEvent(NoticeEvent):
    """用户喊话事件，表示一个广播式的消息"""

    __cmd__: ClassVar[str] = "shout"
    text: str
    """喊话的具体内容"""

    def get_event_description(self) -> str:
        """获取事件描述，返回经过处理的喊话内容"""
        return sanitize(f"Received Shout: {self.text}")


@register_event_class
class OnafkAddEvent(NoticeEvent):
    """Onafk add"""

    __cmd__: ClassVar[str] = "onafkAdd"
    nick: str
    """用户名"""

    def get_event_description(self) -> str:
        """获取事件描述"""
        return sanitize(f"User {self.nick} enters the AFK state")


@register_event_class
class OnafkRemoveEvent(NoticeEvent):
    """Onafk remove"""

    __cmd__: ClassVar[str] = "onafkRemove"
    nick: str
    """用户名"""

    def get_event_description(self) -> str:
        """获取事件描述"""
        return sanitize(f"User {self.nick} exits the AFK state")


@register_event_class
class OnafkRemoveOnlyEvent(NoticeEvent):
    """Onafk remove only"""

    __cmd__: ClassVar[str] = "onafkRemoveOnly"
    nick: str
    """用户名"""

    def get_event_description(self) -> str:
        """获取事件描述"""
        return sanitize(f"User {self.nick} is removed from the AFK state")


@register_event_class
class ChangeNickEvent(NoticeEvent):
    """用户更改昵称事件"""

    __cmd__: ClassVar[str] = "changenick"
    nick: str
    """新的用户昵称"""

    def get_event_description(self) -> str:
        """获取事件描述"""
        return sanitize(f"Self Nickname has been changed to {self.nick}")


@register_event_class
class ListHistoryEvent(NoticeEvent):
    """聊天记录事件，表示获取历史消息"""

    __cmd__: ClassVar[str] = "list"
    text: list[ChatHistory]
    """历史消息列表（按时间倒序排列，最新消息在前）"""

    def get_event_description(self) -> str:
        """获取事件描述"""
        return f"Received {len(self.text)} historical message records"


@register_event_class
class OnPassEvent(NoticeEvent):
    """验证码验证事件"""

    __cmd__: ClassVar[str] = "onpass"
    ispass: bool
    """是否通过验证"""

    def get_event_description(self) -> str:
        """获取事件描述"""
        return f"验证码验证 {'通过' if self.ispass else '未通过'}"
