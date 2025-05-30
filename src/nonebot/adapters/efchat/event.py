from typing import Any, Literal
from copy import deepcopy
from nonebot.adapters import Event as BaseEvent
from nonebot.compat import model_dump, model_validator

from .message import Message, MessageSegment
from .utils import sanitize
from .models import ChatHistory, OnlineUser

class Event(BaseEvent):
    """通用事件"""
    
    self_id: str
    """机器人自身昵称"""
    channel: str
    """房间名称"""
    time: int
    """时间"""
    to_me: bool = False
    
    class Config:
       extra = "ignore"

    def get_event_description(self) -> str:
        return sanitize(str(model_dump(self)))

    def get_plaintext(self) -> str:
        return "".join(str(seg) for seg in msg) if (msg := self.get_message()) else ""

    def is_tome(self) -> bool:
        return self.to_me


class MessageEvent(Event):
    """消息事件"""

    post_type: Literal["message"] = "message"
    message: Message
    """消息内容"""
    original_message: Message
    """原始消息内容"""
    reply: Message = Message("")
    """引用消息(空字段)"""
    isbot: bool = False
    """是否机器人"""
    nick: str = ""
    """发送者昵称"""
    trip: str = ""
    """加密身份标识"""
    message_id: str = ""
    """消息ID(空字段)"""
    
    @model_validator(mode="before")
    def validate_event(cls, values):
        """校验数据并自动处理 message 和 nick"""
        message_type = self.getattr("message_type", "")

        if message_type not in ["whisper", "channel", "html"]:
            raise ValueError(f"不支持的 message_type: '{message_type}'")

        values["nick"] = values.get("from", "") if message_type == "whisper" else values.get("nick", "")
        values["message"] = Message(values.get("msg", "") if message_type == "whisper" else values.get("text", ""))
        values["original_message"] = deepcopy(values["message"])

        return values

    def get_type(self) -> str:
        return "message"

    def get_event_name(self) -> str:
        return f"{self.post_type}.{self.message_type}"

    def get_message(self) -> Message:
        return self.message

    def get_user_id(self) -> str:
        return self.nick

    def get_session_id(self) -> str:
        return ""

    def is_tome(self) -> bool:
        return self.to_me


class ChannelMessageEvent(MessageEvent):
    """房间消息事件"""

    message_type: Literal["channel"] = "channel"
    head: str
    """用户头像链接"""
    level: int
    """等级"""

    def get_event_description(self) -> str:
        return sanitize(f"Message from {self.nick}@[房间:{self.channel}]: {self.message}")

    def get_session_id(self) -> str:
        return f"group_{self.channel}_{self.nick}"


class WhisperMessageEvent(MessageEvent):
    """私聊事件"""

    message_type: Literal["whisper"] = "whisper"
    text: str
    """提示内容"""

    def get_event_description(self) -> str:
        return sanitize(f"Message from {self.nick}: {self.message}")


class HTMLMessageEvent(MessageEvent):
    """HTML消息事件"""

    message_type: Literal["html"] = "html"
    mod: bool = False
    """来自插件"""
    admin: bool = False
    """来自管理员"""

    def get_event_description(self) -> str:
        return sanitize(f"Received HTML Message from {self.nick}: {self.message}")


class NoticeEvent(Event):
    """通知事件"""

    post_type:Literal["notice"] = "notice"
    type: str = ""
    """具体子事件"""
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type = data["cmd"]

    def get_event_name(self) -> str:
        return f"{self.post_type}.{self.type}"

    def get_type(self) -> str:
        return self.post_type

    def get_message(self) -> Message:
        raise ValueError("Event has no message!")

    def get_user_id(self) -> str | int:
        return self.nick if hasattr(self, "nick") else ""

    def get_session_id(self) -> str:
        return self.channel if hasattr(self, channel) else ""


class RequestEvent(Event):
    """请求事件"""
    
    post_type: Literal["request"] = "request"
    type: str = ""
    """具体子事件"""
    text: str
    """事件内容"""
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type = data.get("type") or data["cmd"]

    def get_type(self) -> str:
        return "request"

    def get_message(self) -> Message:
        raise ValueError("Event has no message!")

    def get_event_name(self) -> str:
        return f"{self.post_type}.{self.type}"

    def get_event_description(self) -> str:
        return sanitize(f"Received {self.type} from {self.nick}@[房间:{self.channel}]: {self.text}")

    def get_user_id(self) -> str | int:
        return self.nick if hasattr(self, "nick") else ""

    def get_session_id(self) -> str:
        return self.channel if hasattr(self, channel) else ""


class SystemEvent(NoticeEvent):
    """系统通知事件"""

    event: str = "info"
    """通知具体事件"""
    text: str
    """事件内容"""
    
    def __init__(self, **data):
        super().__init__(**data)
        self.event = data.get("type") or data["cmd"]

    def get_event_description(self) -> str:
        return sanitize(f"{self.event.upper()} from @[房间:{self.channel}]: {self.text}")

    def get_event_name(self) -> str:
        return f"{self.post_type}.{self.type}.{self.event}"


class InviteEvent(RequestEvent):
    """邀请事件"""

    nick: str = ""
    """邀请人"""
    to: str
    """邀请到的房间"""
    
    def __init__(self, **data):
        super().__init__(**data)
        self.nick = data["from"]


class JoinRoomEvent(NoticeEvent):
    """加入房间事件"""

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
    utype: str
    """用户类型"""

    def get_event_description(self) -> str:
        return sanitize(f"User {self.nick}@[trip:{self.trip}] from {self.city} joined 房间:{self.channel}")


class LeaveRoomEvent(NoticeEvent):
    """离开房间事件"""

    nick: str
    """用户名"""

    def get_event_description(self) -> str:
        return sanitize(f"User {self.nick} left the room")


class OnlineSetEvent(NoticeEvent):
    """在线人数事件"""

    nicks: list[str]
    """在线用户列表"""
    users: list[OnlineUser]
    """用户详细信息列表"""
    
    def __init__(self, **data):
        super().__init__(**data)
        self.users = [OnlineUser(**user) for user in data.get("users", [])]
    
    def get_event_description(self) -> str:
        return f"当前房间内共有 {len(self.nicks)} 名用户在线"


class KillEvent(NoticeEvent):
    """封禁事件"""

    nick: str
    """被封禁用户名称"""
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type = data["cmd"]

    def get_event_description(self) -> str:
        return sanitize(f"User {self.nick} has been {self.type}.")


class ShoutEvent(NoticeEvent):
    """用户喊话事件，表示一个广播式的消息"""

    text: str
    """喊话的具体内容"""

    def get_event_description(self) -> str:
        """获取事件描述，返回经过处理的喊话内容"""
        return sanitize(f"Received Shout: {self.text}")


class OnafkAddEvent(NoticeEvent):
    """Onafk add"""

    nick: str
    """用户名"""

    def get_event_description(self) -> str:
        """获取事件描述"""
        return sanitize(f"User {self.nick} enters the AFK state")


class OnafkRemoveEvent(NoticeEvent):
    """Onafk remove"""

    nick: str
    """用户名"""

    def get_event_description(self) -> str:
        """获取事件描述"""
        return sanitize(f"User {self.nick} exits the AFK state")


class OnafkRemoveOnlyEvent(NoticeEvent):
    """Onafk remove only"""

    nick: str
    """用户名"""

    def get_event_description(self) -> str:
        """获取事件描述"""
        return sanitize(f"User {self.nick} is removed from the AFK state")


class ChangeNickEvent(NoticeEvent):
    """用户更改昵称事件"""

    nick: str
    """新的用户昵称"""

    def get_event_description(self) -> str:
        """获取事件描述"""
        return sanitize(f"Self Nickname has been changed to {self.nick}")


class ListHistoryEvent(NoticeEvent):
    """聊天记录事件，表示获取历史消息"""

    text: list[ChatHistory]
    """历史消息列表（按时间倒序排列，最新消息在前）"""

    def __init__(self, **data):
        """初始化事件，并解析历史消息"""
        super().__init__(**data)

        self.text = [ChatHistory(**msg) for msg in data.get("text", [])]

    def get_event_description(self) -> str:
        """获取事件描述"""
        return f"Received {len(self.text)} historical message records"


class OnPassEvent(NoticeEvent):
    """验证码验证事件"""

    ispass: bool
    """是否通过验证"""

    def get_event_description(self) -> str:
        """获取事件描述"""
        return f"验证码验证 {'通过' if self.ispass else '未通过'}"
