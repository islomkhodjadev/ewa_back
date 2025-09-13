# handlers/tree.py (или вынеси в filters.py)
from aiogram.filters import BaseFilter
from aiogram import types
from telegram.models import ButtonTree
from telegram_client.models import BotClientSession


BACK_BTN = "⬅️ Назад"


EXCLUDE_TEXTS = {"Виртуальный помощник", "Личный кабинет"}


class TreeButtonsOnly(BaseFilter):
    async def __call__(self, message: types.Message, session: BotClientSession) -> bool:
        text = (message.text or "").strip()
        if not text:
            return False
        if text in EXCLUDE_TEXTS:
            return False
        if text == BACK_BTN:
            return True

        # На корне: разрешаем только тексты корневых кнопок
        if session.current_button is None:
            return await ButtonTree.objects.filter(parent=None, text=text).aexists()

        # В глубине: разрешаем только тексты детей текущей кнопки
        return await session.current_button.children.filter(text=text).aexists()
