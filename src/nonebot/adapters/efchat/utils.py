import asyncio
import httpx
from typing import Union
from nonebot.utils import logger_wrapper
from .exception import NetworkError

log = logger_wrapper("EFChat")

def sanitize(message: str) -> str:
    """将 `<` 和 `>` 转换为 HTML 实体编码"""
    return message.replace("<", "&lt;").replace(">", "&gt;")


async def download_audio(url: str) -> bytes:
    """从 URL 下载音频文件并返回 `bytes` 数据"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as e:
            raise ActionFail(e.response)
        except httpx.RequestError as e:
            raise NetworkError(f"语音 {url} 下载失败: {e}")

async def upload_voice(url: Union[str, None], path: Union[str, None], raw: Union[bytes, None]) -> str:
    """上传语音文件并返回 `src_name`"""
    if raw:
        file_data = raw
    elif path:
        file_data = await asyncio.create_task(_read_audio_file(path))
    elif url:
        file_data = await download_audio(url)
    else:
        raise ValueError("音频数据无效，无法上传")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://efchat.melon.fish/voice",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
                    "Origin": "https://efchat.melon.fish",
                    "Referer": "https://efchat.melon.fish/",
                },
                files={
                    "upfile": ("voice.mp3", file_data, "audio/mpeg"),
                    "cmd": (None, "chat")
                }, 
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ActionFail(e.response)
        except httpx.RequestError as e:
            raise NetworkError(str(e))
        try:
            result = response.json()
        except Exception as e:
            raise ActionFailed(response)
        src = result.get("src")
        if not src:
            logger.warning("语音上传:响应中未找到 'src' 字段")
        return src


async def _read_audio_file(path: str) -> bytes:
    """异步读取本地音频文件"""
    with open(path, "rb") as f:
        return f.read()

class logger:
    @classmethod
    def log(cls, level, msg):
        try:
            log(level, msg)
        except Exception as e:
            log(level, sanitize(msg))

    @classmethod
    def debug(cls, msg):
        cls.log("DEBUG", msg)

    @classmethod
    def warning(cls, msg):
        cls.log("WARNING", msg)

    @classmethod
    def error(cls, msg):
        cls.log("ERROR", msg)

    @classmethod
    def critical(cls, msg):
        cls.log("CRITICAL", msg)

    @classmethod
    def success(cls, msg):
        cls.log("SUCCESS", msg)

    @classmethod
    def info(cls, msg):
        cls.log("INFO", msg)
