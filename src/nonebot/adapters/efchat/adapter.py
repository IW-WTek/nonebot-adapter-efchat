import json
import asyncio
import re
from typing import Dict, Optional, Callable, Awaitable
from nonebot.adapters import Adapter as BaseAdapter
from nonebot.exception import WebSocketClosed
from nonebot.drivers import Request, WebSocketClientMixin, Driver

from .config import Config
from .bot import Bot
from .const import EVENT_MAP
from .log import log
from .event import WhisperMessageEvent, ChannelMessageEvent

class Adapter(BaseAdapter):
    """EFChat 适配器，统一管理 WebSocket 连接、Bot 实例以及心跳包"""

    def __init__(self, driver: Driver, **kwargs):
        super().__init__(driver, **kwargs)
        self.cfg: Config = Config()
        self.bots: Dict[str, Bot] = {}  # 维护所有 Bot
        self._bot_tasks = []  # 存储所有 WebSocket 连接任务

    @classmethod
    def get_name(cls) -> str:
        return "EFChat"

    def setup(self) -> None:
        """初始化适配器，注册启动与关闭回调"""
        if not isinstance(self.driver, WebSocketClientMixin):
            raise RuntimeError(f"{self.get_name()} 需要 WebSocket Client Driver!")
        self.driver.on_startup(self.startup)
        self.driver.on_shutdown(self.shutdown)

    async def startup(self):
        """启动所有 Bot，并管理 WebSocket 任务"""
        for bot_config in self.cfg.efchat_bots:
            bot = Bot(self, bot_config)
            self.bots[bot.bot_id] = bot

            ws_task = asyncio.create_task(self._forward_ws(bot))
            heartbeat_task = asyncio.create_task(self._heartbeat(bot))

            self._bot_tasks.extend([ws_task, heartbeat_task])

    async def shutdown(self) -> None:
        """关闭所有 Bot 并清理任务"""
        for bot in self.bots.values():
            await bot.disconnect_ws()

        for task in self._bot_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._bot_tasks.clear()

    async def _forward_ws(self, bot: Bot):
        """管理 WebSocket 连接，正确传递 login_data"""
        url = "wss://efchat.melon.fish/ws"
        request = Request("GET", url)
    
        while True:
            try:
                async with self.websocket(request) as ws:
                    bot.ws = ws
                    login_data = {
                        "cmd": "join",
                        "nick": bot.nick,
                        "head": bot.head,
                        "channel": bot.channel,
                        "client_key": "EFChat_Bot"
                    }
                    if bot.password:
                        login_data["password"] = bot.password
                    elif bot.token:
                        login_data["token"] = bot.token
    
                    await bot.send_packet(login_data)
    
                    self.handle_connect(bot)  # 确保触发连接成功逻辑
    
                    while True:
                        raw_data = await ws.receive()
                        data = json.loads(raw_data)
                        await self._handle_data(bot, data)
    
            except WebSocketClosed:
                log("ERROR", f"Bot {bot.bot_id} WebSocket 连接关闭")
                await asyncio.sleep(5)
    
            except Exception as e:
                log("ERROR", f"Bot {bot.bot_id} WebSocket 错误: {e}")
                await asyncio.sleep(5)

    async def _heartbeat(self, bot: Bot):
        """维护 WebSocket 连接心跳包，避免断连"""
        try:
            while True:
                try:
                    await asyncio.sleep(30)
                    await bot.send_packet({"cmd": "ping"})
                except Exception as e:
                    log("ERROR", f"Bot {bot.bot_id} 心跳包发送失败: {e}")
                    import traceback
                    traceback.print_exc()
                    break
        except asyncio.CancelledError:
            pass

    async def _handle_data(self, bot: Bot, data: dict):
        """处理 WebSocket 收到的事件"""
        try:
            if data.get("channel") is None:
                data["channel"] = bot.channel

            if event_cls := EVENT_MAP.get(data.get("cmd")):
                event = event_cls(**data, self_id=bot.bot_id)
                if not (
                    isinstance(event, (ChannelMessageEvent, WhisperMessageEvent))
                    and self.cfg.efchat_ignore_self
                    and event.nick == bot.nick
                ):
                    await bot.handle_event(event)
            elif data.get("cmd") == "cap":
                await self._handle_captcha(bot, data)
            else:
                log("WARNING", f"未知事件: {data}")
        except Exception as e:
            log("ERROR", f"事件处理错误: {e}")

    async def _handle_captcha(self, bot: Bot, data: dict, captcha_callback: Optional[Callable[[str], Awaitable[str]]] = None, timeout: int = 60):
        """处理验证码事件"""
        log("WARNING", "触发验证码验证，请输入验证码后继续")

        match = re.findall(r'!\[]\((.*?)\)', data.get("text", ""))
        captcha_url = f"https://efchat.melon.fish/{match[0]}" if match else data.get("text", "")

        log("INFO", f"验证码地址: {captcha_url}")

        if captcha_callback is None:
            captcha_callback = lambda url: asyncio.get_event_loop().run_in_executor(None, input, f"请输入验证码（{url}）: ")

        captcha = None
        if captcha_callback:
            try:
                captcha = await asyncio.wait_for(captcha_callback(captcha_url), timeout=timeout)
            except asyncio.TimeoutError:
                log("ERROR", "验证码输入超时，跳过本次验证码处理")
        else:
            log("WARNING", "未提供 captcha_callback，跳过验证码输入")

        if captcha:
            await bot.send_packet({"cmd": "chat", "text": captcha})

    def handle_connect(self, bot: Bot):
        """Bot 连接成功时调用"""
        log("SUCCESS", f"Bot {bot.bot_id} 连接成功")

    def handle_disconnect(self, bot: Bot):
        """Bot 断开连接时调用"""
        log("INFO", f"Bot {bot.bot_id} 断开连接")

    async def _call_api(self, bot: Bot, api: str, **kwargs):
        """适配器统一管理 Bot 的 API 调用"""
        log("DEBUG", f"Bot {bot.bot_id} 调用 API <y>{api}</y>")
        await bot.send_packet({"cmd": api, **kwargs})
