from typing import Optional
from pydantic import BaseModel


class OnlineUser(BaseModel):
    """用户信息模型"""

    nick: str
    """用户名称"""
    trip: str
    """加密身份标识"""
    utype: str
    """用户类型"""
    hash: str
    """用户Hash"""
    level: int
    """用户等级"""
    userid: int
    """用户ID"""
    channel: str
    """所在房间"""
    isme: bool
    """是否为用户本身"""

    class Config:
        extra = "ignore"


class ChatHistory(BaseModel):
    """聊天记录基本模型"""

    id: int
    """消息Id"""
    channel: str
    """房间名称"""
    nick: str
    """用户名称"""
    content: str
    """消息内容"""
    time: str
    """发送时间"""
    show: int
    """是否显示在聊天记录内"""
    head: str
    """用户头像"""
    trip: str
    """加密身份标识"""

    class Config:
        extra = "ignore"


class EFChatBotConfig(BaseModel):
    nick: str = "EFChatBot"
    """账号昵称"""
    password: Optional[str] = None
    """账号密码"""
    channel: str = "PublicR"
    """活跃房间"""
    head: str = "https://efchat.melon.fish/imgs/ava.png"
    """头像链接"""
    token: Optional[str] = None
    """认证Token"""
    ignore_self: bool = True
    """忽略自身消息"""
