from pydantic import BaseModel, Field
from .models import EFChatBot

class Config(BaseModel):
    efchat_bots: list[EFChatBot] = Field(default_factory=list)
    """efchat配置"""
    efchat_ignore_self: bool = True
    """忽略自身消息"""
