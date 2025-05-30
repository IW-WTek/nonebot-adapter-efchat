from typing import Optional
from nonebot.exception import AdapterException
from nonebot.exception import NetworkError as BaseNetworkError


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