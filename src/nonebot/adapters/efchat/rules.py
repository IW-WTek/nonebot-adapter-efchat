from typing import Union
from nonebot.internal.rule import Rule
from .event import Event


def notice_rule(event_type: Union[type, list[type]]) -> Rule:
    """
    Notice限制

    参数:
        event_type: Event类型

    返回:
        Rule: Rule
    """

    async def _rule(event: Event) -> bool:
        if isinstance(event_type, list):
            for et in event_type:
                if isinstance(event, et):
                    return True
        else:
            return isinstance(event, event_type)
        return False

    return Rule(_rule)
