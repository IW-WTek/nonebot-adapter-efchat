from pydantic import BaseModel, Extra
import nonebot

class Config(BaseModel):
   
    efchat_name: str = "EFChatBot"
    """Bot账号"""
    nickname: list[str] = [""]
    """Bot昵称"""
    efchat_channel: str = "PublicR"
    """Bot活跃的Channel"""
    efchat_head: str = "https://efchat.melon.fish/imgs/ava.png"
    """头像地址"""
    efchat_password: str | None = None
    """Bot账号密码"""
    efchat_token: str | None = None
    """Bot Token"""
    efchat_ignore_self: bool = True
    """忽略自身消息"""
