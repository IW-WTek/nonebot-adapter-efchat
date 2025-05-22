from pydantic import BaseModel, Extra
import nonebot

class Config(BaseModel):
   
    efchat_name: str = "EFChatBot"
    """Bot名称"""
    efchat_channel: str = "default"
    """Bot活跃的Channel"""
    efchat_head: str = "https://efchat.melon.fish/imgs/ava.png"
    """头像地址"""
    efchat_token: str | None = None
    """Bot Token"""
    efchat_ignore_self: bool = True
    """忽略自身消息"""

class PluginConfig(BaseModel, extra=Extra.ignore):
    nickname: list[str] = ["Bot", "bot"]

plugin_config: PluginConfig = PluginConfig.parse_obj(
    nonebot.get_driver().config.dict(exclude_unset=True)
)

nickname_list = plugin_config.nickname
