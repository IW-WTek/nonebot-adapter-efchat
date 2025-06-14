from pydantic import BaseModel, Field
from .models import EFChatBotConfig


class Config(BaseModel):
    efchat_bots: list[EFChatBotConfig] = Field(default_factory=list)
    """efchat配置"""

