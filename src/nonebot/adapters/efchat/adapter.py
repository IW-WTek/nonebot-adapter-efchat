import contextlib
import json
import re
import asyncio
from typing import Any, Optional
from nonebot import get_plugin_config
from nonebot.adapters import Adapter as BaseAdapter
from nonebot.exception import WebSocketClosed
from nonebot.drivers import Request, WebSocketClientMixin, Driver, HTTPClientMixin, WebSocket

from .models import EFChatBot

from .config import Config
from .bot import Bot
from .const import EVENT_MAP
from .event import WhisperMessageEvent, ChannelMessageEvent
from .utils import logger


async def heartbeat(adapter: "Adapter", bot: EFChatBot):
    """发送心跳包"""
    while True:
        try:
            await asyncio.sleep(delay=30)
            await adapter.send_packet(bot, {"cmd": "ping"})
        except Exception as e:
            logger.error(f"心跳包发送失败: {e}")
            break


class Adapter(BaseAdapter):
    """EFChat 适配器"""

    def __init__(self, driver: Driver, **kwargs):
        super().__init__(driver, **kwargs)
        self.cfg = get_plugin_config(Config)
        self.task: Optional[asyncio.Task] = None
        self.bots_ws: dict[str, WebSocket] = {}
        self.setup()

    @classmethod
    def get_name(cls) -> str:
        return "EFChat"

    def setup(self) -> None:
        """适配器初始化"""
        if not isinstance(self.driver, WebSocketClientMixin):
            raise RuntimeError(f"{self.get_name()} 需要 WebSocket Client Driver!")
        elif not isinstance(self.driver, HTTPClientMixin):
            raise RuntimeError(f"{self.get_name()} 需要 HTTP Client Driver!")
        self.on_ready(self.connect_ws)
        self.driver.on_shutdown(self.shutdown)

    async def connect_ws(self):
        """连接 WebSocket"""
        for bot in self.cfg.efchat_bots:
            self.task = asyncio.create_task(self._forward_ws(bot))

    async def _call_api(self, bot: EFChatBot, api: str, **kwargs):
        logger.debug(f"Bot {bot.nick} calling API <y>{api}</y>")
        await self.send_packet(bot, {"cmd": api, **kwargs})

    async def _forward_ws(self, bot: EFChatBot):
        """WebSocket 连接维护"""
        url = "wss://efchat.melon.fish/ws"
        pwd = bot.password
        token = bot.token
        request = Request(method="GET", url=url)
        tasks = []

        while True:  # 自动重连
            try:
                async with self.websocket(request) as ws:
                    self.bots_ws[bot.nick] = ws
                    logger.success("WebSocket 连接已建立")
                    for task in tasks:
                        if not task.done():
                            try:
                                task.cancel()
                            except Exception as e:
                                logger.warning(
                                    f"任务 {task.get_coro().__name__} 终止失败: {e}"
                                )
                        tasks.clear()
                    login_data = {
                        "cmd": "join",
                        "nick": bot.nick,
                        "head": bot.head,
                        "channel": bot.channel,
                        "client_key": "EFChat_Bot",
                    }
                    if pwd:
                        login_data["password"] = pwd
                    if token:
                        login_data["token"] = token
                    else:
                        raise ValueError("Token是必填项")

                    await self.send_packet(bot, login_data)
                    logger.debug("登录请求已发送")

                    self._handle_connect(bot)
                    tasks.append(asyncio.create_task(heartbeat(self, bot)))

                    while True:
                        raw_data = await ws.receive()
                        logger.debug(f"接收到数据: {raw_data}")
                        try:
                            data = json.loads(raw_data)
                            await self._handle_data(data, bot)
                        except json.JSONDecodeError:
                            logger.warning(f"数据包解析失败: {raw_data}")

            except WebSocketClosed as e:
                logger.error(f"WebSocket 关闭: {e}")
                self._handle_disconnect(bot)
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket 错误: {e}")
                self._handle_disconnect(bot)
                await asyncio.sleep(5)

    async def _handle_data(self, data, bot: EFChatBot):
        """处理事件"""
        try:
            if data.get("channel") is None:
                data["channel"] = bot.channel
            if (
                data["cmd"] == "info"
                and data.get("type") == "whisper"
                and data.get("from") is not None
            ):
                event_cls = EVENT_MAP["whisper"]
            else:
                event_cls = EVENT_MAP.get(data["cmd"])
            if event_cls:
                event = event_cls(**data, self_id=bot.nick)

                bot_ = Bot(self, bot.nick, bot)

                # 过滤自身消息（私聊和房间消息）
                if not (
                    isinstance(event, (ChannelMessageEvent, WhisperMessageEvent))
                    and self.cfg.efchat_ignore_self
                    and event.nick == bot.nick
                ):
                    await Bot.handle_event(bot_, event)

            elif data["cmd"] == "cap":
                await self._handle_captcha(bot, data)

            else:
                logger.warning(f"未知事件: {data}")

        except Exception as e:
            logger.error(f"事件处理错误: {type(e)}: {e}")

    async def _handle_captcha(self, bot, data):
        """处理验证码事件"""
        logger.warning("触发验证码验证，请输入验证码后继续")
        match = re.findall(r"!\[]\((.*?)\)", data["text"])
        captcha_url = f"https://efchat.melon.fish/{match[0]}" if match else data["text"]
        logger.info(f"验证码地址: {captcha_url}")

        captcha = await asyncio.get_event_loop().run_in_executor(
            None, input, "请输入验证码: "
        )
        await self.send_packet(bot, {"cmd": "chat", "text": captcha})

    async def shutdown(self) -> None:
        """关闭 WebSocket"""
        if self.task and not self.task.done():
            self.task.cancel()
        for bot in self.cfg.efchat_bots:
            self._handle_disconnect(bot)

    def _handle_connect(self, bot):
        """处理连接"""
        bot_ = Bot(self, bot.nick, bot)
        self.bot_connect(bot_)
        logger.success(f"Bot {bot.nick} 已连接")

    def _handle_disconnect(self, bot):
        """处理断开连接"""
        bot_ = Bot(self, bot.nick, bot)
        with contextlib.suppress(Exception):
            self.bot_disconnect(bot_)
        logger.info(f"Bot {bot.nick} 已断开")

    async def send_packet(self, bot: EFChatBot, data: dict[str, Any]):
        """发送数据包"""
        await self.bots_ws[bot.nick].send(json.dumps(data))
