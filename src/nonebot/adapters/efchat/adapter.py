import json
import re
import asyncio
from typing import Optional
from nonebot import get_plugin_config, logger
from nonebot.adapters import Adapter as BaseAdapter
from nonebot.exception import WebSocketClosed
from nonebot.drivers import Request, WebSocketClientMixin, Driver

from .config import Config
from .bot import Bot
from .const import EVENT_MAP
from .event import WhisperMessageEvent, ChannelMessageEvent

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
        self.adapter_config = get_plugin_config(Config)
        self.self_id = self.adapter_config.efchat_name
        self.head = self.adapter_config.efchat_head
        self.channel = self.adapter_config.efchat_channel
        self.task: Optional[asyncio.Task] = None
        self.setup()

    @classmethod
    def get_name(cls) -> str:
        return "EFChat"

    def setup(self) -> None:
        """适配器初始化"""
        if not isinstance(self.driver, WebSocketClientMixin):
            raise RuntimeError(f"{self.get_name()} 需要 WebSocket Client Driver!")
        self.driver.on_startup(self.startup)
        self.driver.on_shutdown(self.shutdown)

    async def startup(self):
        """连接 WebSocket"""
        self.task = asyncio.create_task(self._forward_ws())

    async def _call_api(self, api: str, **kwargs):
        await self.adapter.send_packet({"cmd": api, **kwargs})

    async def _forward_ws(self):
        """WebSocket 连接维护"""
        url = "wss://efchat.melon.fish/ws"
        request = Request(method="GET", url=url)

        while True:  # 自动重连
            try:
                async with self.websocket(request) as ws:
                    self.ws = ws
                    logger.success("WebSocket 连接已建立")

                    await self.send_packet({
                        "cmd": "join",
                        "nick": self.self_id,
                        "head": self.head,
                        "channel": self.channel,
                        "token": self.adapter_config.efchat_token,
                        "client_key": "EFChat_Bot"
                    })
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
            event_cls = EVENT_MAP.get(data["cmd"])
            if event_cls:
                event = event_cls(**data, self_id=self.self_id, channel=self.channel)
    
                bot = Bot(self, self.self_id)
    
                # 过滤自身消息（私聊和房间消息）
                if not (
                    isinstance(event, (ChannelMessageEvent, WhisperMessageEvent))
                    and self.adapter_config.efchat_ignore_self
                    and event.nick == self.self_id
                ):
                    await Bot.handle_event(bot, event)
    
            elif data["cmd"] == "cap":
                await self._handle_captcha(data)
    
            else:
                logger.warning(f"未知事件: {data}")
    
        except Exception as e:
            logger.error(f"事件处理错误: {e}")

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
        bot = Bot(self, self.self_id)
        self.bot_connect(bot)
        logger.success(f"Bot {self.self_id} 已连接")

    def _handle_disconnect(self):
        """处理断开连接"""
        bot = Bot(self, self.self_id)
        try:
            self.bot_disconnect(bot)
        except Exception:
            pass
        logger.info(f"Bot {self.self_id} 已断开")

    async def send_packet(self, data: dict):
        """发送数据包"""
        await self.ws.send(json.dumps(data))
