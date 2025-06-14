import contextlib
import json
from typing import Optional, Union
from nonebot.drivers import Response
from nonebot.exception import AdapterException
from nonebot.exception import NetworkError as BaseNetworkError
from nonebot.exception import ActionFailed as BaseActionFailed


class EFChatAdapterException(AdapterException):
    def __init__(self):
        super().__init__("EFChat")


class NetworkError(BaseNetworkError, EFChatAdapterException):
    def __init__(self, msg: Optional[str] = None):
        super().__init__()
        self.msg: Optional[str] = msg
        """错误原因"""

    def __repr__(self):
        return f"<NetWorkError message={self.msg}>"

    def __str__(self):
        return self.__repr__()


class ActionFailed(BaseActionFailed, EFChatAdapterException):
    def __init__(self, response: Response):
        self.status_code: int = response.status_code
        self.code: Optional[int] = response.status_code
        self.message: Optional[Union[str, bytes]] = response.content
        self.data: Optional[dict] = None
        with contextlib.suppress(Exception):
            if self.message:
                self.data: Optional[dict] = json.loads(self.message)
