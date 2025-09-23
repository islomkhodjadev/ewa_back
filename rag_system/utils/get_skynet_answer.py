from . import skynet
from typing import Optional, Dict
from miniapp.models import ChatSession


async def get_answer__skynet_async(prompt: str, session: ChatSession) -> Optional[Dict]:

    result = await skynet.skynet_answer_async(prompt, session)

    return result


def get_answer__skynet_sync(prompt: str, session: ChatSession) -> Optional[Dict]:

    result = skynet.skynet_answer(prompt, session)

    return result
