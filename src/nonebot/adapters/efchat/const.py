from .event import (
    JoinRoomEvent, LeaveRoomEvent, ChannelMessageEvent, WhisperMessageEvent, SystemEvent, 
    OnlineSetEvent, HTMLMessageEvent, KillEvent, ShoutEvent, OnafkAddEvent, OnafkRemoveEvent, 
    OnafkRemoveOnlyEvent, ChangeNickEvent, ListHistoryEvent, OnPassEvent, InviteEvent
)

# 事件映射字典
EVENT_MAP = {
    "onlineAdd": JoinRoomEvent,
    "onlineRemove": LeaveRoomEvent,
    "chat": ChannelMessageEvent,
    "info": SystemEvent,
    "shout": ShoutEvent,
    "warn": SystemEvent,
    "cap": SystemEvent,
    "onlineSet": OnlineSetEvent,
    "html": HTMLMessageEvent,
    "kill": KillEvent,
    "unkill": KillEvent,
    "onafkAdd": OnafkAddEvent,
    "onafkRemove": OnafkRemoveEvent,
    "onafkRemoveOnly": OnafkRemoveOnlyEvent,
    "changenick": ChangeNickEvent,
    "list": ListHistoryEvent,
    "onpass": OnPassEvent,
    "invite": InviteEvent
}
