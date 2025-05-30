import asyncio
import httpx
from typing import Union
from nonebot.utils import logger_wrapper
from .exception import NetworkError

log = logger_wrapper("EFChat")

def sanitize(message: str) -> str:
    """将 `<` 和 `>` 转换为 HTML 实体编码"""
    return message.replace("<", "&lt;").replace(">", "&gt;")

async def upload_voice(path: Union[str, None], raw: Union[bytes, None]) -> str:
    """上传语音文件并返回 src_name"""
    if raw:
        file_data = raw
    elif path:
        file_data = await asyncio.create_task(_read_audio_file(path))
    else:
        raise ValueError("音频数据无效，无法上传")

    boundary = _get_boundary()
    
    async with httpx.AsyncClient() as client:
        try:

            response = await client.post(
                "https://efchat.melon.fish/voice",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
                    "Origin": "https://efchat.melon.fish",
                    "Referer": "https://efchat.melon.fish/",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                content=_build_multipart_body(boundary, "voice.mp3", file_data),
            )
        except httpx.HTTPError as e:
            raise NetworkError(msg=f"{type(e)}:{e}")
        result = response.json()
        src = result.get("src")
        if not src:
            logger.warning("语音上传:响应中未找到 'src' 字段")
    
        return src


async def _read_audio_file(path: str) -> bytes:
    """异步读取本地音频文件"""
    async with asyncio.Lock():
        with open(path, "rb") as f:
            return f.read()


def _get_boundary() -> str:
    """生成 multipart/form-data 请求的 boundary"""
    return f"----WebKitFormBoundary{os.urandom(16).hex()}"


def _build_multipart_body(boundary: str, file_name: str, file_data: bytes) -> bytes:
    """构建 multipart/form-data 请求体"""
    content = [f"--{boundary}".encode()]
    content.extend([
        f'Content-Disposition: form-data; name="upfile"; filename="{file_name}"'.encode(),
        b"Content-Type: audio/mpeg",
        b"",
        file_data,
    ])
    content.extend([
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="cmd"',
        b"",
        b"chat",
    ])
    content.extend([f"--{boundary}--".encode(), b""])
    return b"\r\n".join(content)

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