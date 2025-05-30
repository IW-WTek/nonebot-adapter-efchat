import json
import re
import asyncio
from typing import Optional
from nonebot import get_plugin_config
from nonebot.adapters import Adapter as BaseAdapter
from nonebot.exception import WebSocketClosed
from nonebot.drivers import Request, WebSocketClientMixin, Driver

from .config import Config
from .bot import Bot
from .const import EVENT_MAP
from .event import WhisperMessageEvent, ChannelMessageEvent
from .utils import logger

async def heartbeat(adapter):
    """发送心跳包"""
    while True:
        try:
            await asyncio.sleep(30)
            await adapter.send_packet({"cmd": "ping"})
        except Exception as e:
            logger.error(f"心跳包发送失败: {e}")
            break

class Adapter(BaseAdapter):
    """EFChat 适配器"""

    def __init__(self, driver: Driver, **kwargs):
        super().__init__(driver, **kwargs)
        self.cfg = get_plugin_config(Config)
        # TODO: 支持多Bot
        self.bot = self.cfg.efchat_bots[0]
        self.task: Optional[asyncio.Task] = None
        self.setup()

    @classmethod
    def get_name(cls) -> str:
        return "EFChat"

    def setup(self) -> None:
        """适配器初始化"""
        if not isinstance(self.driver, WebSocketClientMixin):
            raise RuntimeError(f"{self.get_name()} 需要 WebSocket Client Driver!")
        self.on_ready(self.connect_ws)
        self.driver.on_shutdown(self.shutdown)

    async def connect_ws(self):
        """连接 WebSocket"""
        self.task = asyncio.create_task(self._forward_ws())

    async def _call_api(self, api: str, **kwargs):
        logger.debug(f"Bot {self.bot.nick} calling API <y>{api}</y>")
        await self.send_packet({"cmd": api, **kwargs})

    async def _forward_ws(self):
        """WebSocket 连接维护"""
        url = "wss://efchat.melon.fish/ws"
        pwd = self.bot.password
        token = self.bot.token
        request = Request(method="GET", url=url)

        while True:  # 自动重连
            try:
                async with self.websocket(request) as ws:
                    self.ws = ws
                    logger.success("WebSocket 连接已建立")
                    login_data = {
                        "cmd": "join",
                        "nick": self.bot.nick,
                        "head": self.bot.head,
                        "channel": self.bot.channel,
                        "client_key": "EFChat_Bot"
                    }
                    if pwd:
                        login_data["password"] = self.bot.password
                    if token:
                        login_data["token"] = self.bot.token
                    else:
                        raise ValueError("Token是必填项")

                    await self.send_packet(login_data)
                    logger.debug("登录请求已发送")

                    self._handle_connect()
                    asyncio.create_task(heartbeat(self))

                    while True:
                        raw_data = await ws.receive()
                        logger.debug(f"接收到数据: {raw_data}")
                        try:
                            data = json.loads(raw_data)
                            await self._handle_data(data)
                        except json.JSONDecodeError:
                            logger.warning(f"数据包解析失败: {raw_data}")

            except WebSocketClosed as e:
                logger.error(f"WebSocket 关闭: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket 错误: {e}")
                await asyncio.sleep(5)

    async def _handle_data(self, data):
        """处理事件"""
        try:
            if data.get("channel") is None:
                data["channel"] = self.bot.channel
            if data["cmd"] == "info" and data.get("type") == "whisper":
                event_cls = EVENT_MAP["whisper"]
            else:
                event_cls = EVENT_MAP.get(data["cmd"])
            if event_cls:
                event = event_cls(**data, self_id=self.bot.nick)
    
                bot = Bot(self, self.bot.nick)
    
                # 过滤自身消息（私聊和房间消息）
                if not (
                    isinstance(event, (ChannelMessageEvent, WhisperMessageEvent))
                    and self.cfg.efchat_ignore_self
                    and event.nick == self.bot.nick
                ):
                    await Bot.handle_event(bot, event)
    
            elif data["cmd"] == "cap":
                await self._handle_captcha(data)
    
            else:
                logger.warning(f"未知事件: {data}")
    
        except Exception as e:
            logger.error(f"事件处理错误: {type(e)}: {e}")

    async def _handle_captcha(self, data):
        """处理验证码事件"""
        logger.warning("触发验证码验证，请输入验证码后继续")
        match = re.findall(r'!\[]\((.*?)\)', data["text"])
        captcha_url = f"https://efchat.melon.fish/{match[0]}" if match else data["text"]
        logger.info(f"验证码地址: {captcha_url}")

        captcha = await asyncio.get_event_loop().run_in_executor(None, input, "请输入验证码: ")
        await self.send_packet({"cmd": "chat", "text": captcha})

    async def shutdown(self) -> None:
        """关闭 WebSocket"""
        if self.task and not self.task.done():
            self.task.cancel()
        self._handle_disconnect()

    def _handle_connect(self):
        """处理连接"""
        bot = Bot(self, self.bot.nick)
        self.bot_connect(bot)
        logger.success(f"Bot {self.bot.nick} 已连接")

    def _handle_disconnect(self):
        """处理断开连接"""
        bot = Bot(self, self.bot.nick)
        try:
            self.bot_disconnect(bot)
        except Exception:
            pass
        logger.info(f"Bot {self.bot.nick} 已断开")

    async def send_packet(self, data: dict):
        """发送数据包"""
        await self.ws.send(json.dumps(data))
