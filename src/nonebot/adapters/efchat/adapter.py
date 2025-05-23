import json
import asyncio
import re
from typing import Dict, Optional
from nonebot import get_plugin_config, logger
from nonebot.adapters import Adapter as BaseAdapter
from nonebot.exception import WebSocketClosed
from nonebot.drivers import Request, WebSocketClientMixin, Driver

from .config import Config
from .bot import Bot
from .const import EVENT_MAP
from .event import WhisperMessageEvent, ChannelMessageEvent

class Adapter(BaseAdapter):
    """EFChat 适配器"""

    def __init__(self, driver: Driver, **kwargs):
        super().__init__(driver, **kwargs)
        self.cfg: Config = get_plugin_config(Config)
        self.bots: Dict[str, Bot] = {}  # 使用 "nick@channel" 作为 key 存放 Bot 实例
        self.setup()

    @classmethod
    def get_name(cls) -> str:
        return "EFChat"

    def setup(self) -> None:
        """适配器初始化：注册启动与关闭回调"""
        if not isinstance(self.driver, WebSocketClientMixin):
            raise RuntimeError(f"{self.get_name()} 需要 WebSocket Client Driver!")
        self.driver.on_startup(self.startup)
        self.driver.on_shutdown(self.shutdown)

    async def startup(self):
        """启动所有 Bot 的 WebSocket 连接"""
        for bot_config in self.cfg.efchat_bots:
            bot = Bot(self, **bot_config)
            key = f"{bot.nick}@{bot.channel}"
            self.bots[key] = bot
            asyncio.create_task(bot.connect_ws())
            asyncio.create_task(self._heartbeat(bot))
        logger.success("所有 Bot 启动任务已创建")

    async def shutdown(self) -> None:
        """关闭所有 Bot 的 WebSocket 连接"""
        for bot in self.bots.values():
            await bot.disconnect_ws()
        logger.info("所有 Bot 的 WebSocket 连接已关闭")

    async def _heartbeat(self, bot: Bot):
        """心跳包维护，防止 WebSocket 断连"""
        while True:
            try:
                await asyncio.sleep(30)
                await bot.send_packet({"cmd": "ping"})
            except Exception as e:
                logger.error(f"Bot {bot.nick}@{bot.channel} 心跳包发送失败: {e}")
                break

    def handle_connect(self, bot: Bot):
        """Bot 连接成功时调用"""
        self.bot_connect(bot)
        logger.success(f"Bot {bot.nick}@{bot.channel} 连接成功")

    def handle_disconnect(self, bot: Bot):
        """Bot 断开连接时调用"""
        try:
            self.bot_disconnect(bot)
        except Exception:
            pass
        logger.info(f"Bot {bot.nick}@{bot.channel} 断开连接")

    async def _handle_data(self, bot: Bot, data: dict):
        """处理由 Bot 接收到的数据，并解析为事件"""
        try:
            if data.get("channel") is None:
                data["channel"] = bot.channel

            event_cls = EVENT_MAP.get(data.get("cmd"))
            if event_cls:
                event = event_cls(**data, self_id=f"{bot.nick}@{bot.channel}")
                if not (
                    isinstance(event, (ChannelMessageEvent, WhisperMessageEvent))
                    and self.cfg.efchat_ignore_self
                    and event.nick == bot.nick
                ):
                    await bot.handle_event(event)
            elif data.get("cmd") == "cap":
                await self._handle_captcha(bot, data)
            else:
                logger.warning(f"未知事件: {data}")
        except Exception as e:
            logger.error(f"事件处理错误: {e}")

    async def _handle_captcha(self, bot: Bot, data: dict):
        """处理验证码事件"""
        logger.warning("触发验证码验证，请输入验证码后继续")
        match = re.findall(r'!\[]\((.*?)\)', data.get("text", ""))
        captcha_url = f"https://efchat.melon.fish/{match[0]}" if match else data.get("text", "")
        logger.info(f"验证码地址: {captcha_url}")
        captcha = await asyncio.get_event_loop().run_in_executor(None, input, "请输入验证码: ")
        await bot.send_packet({"cmd": "chat", "text": captcha})

    async def _call_api(self, bot: Bot, api: str, **kwargs):
        """调用 API 方法"""
        logger.debug(f"Bot {bot.nick}@{bot.channel} calling API <y>{api}</y>")
        await bot.send_packet({"cmd": api, **kwargs})
