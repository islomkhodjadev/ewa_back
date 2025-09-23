from aiogram.utils.keyboard import ReplyKeyboardBuilder
import aiogram
from pydantic import BaseModel
from typing import Optional
from telegram.models import ButtonTree
from aiogram.types import WebAppInfo
from django.conf import settings


class ReplyButton(BaseModel):
    text: str
    request_contact: Optional[bool] = False
    request_location: Optional[bool] = False
    web_app_url: Optional[str] = None

    def to_button_kwargs(self) -> dict:
        """Return only the set kwargs for aiogram's builder.button."""
        kwargs = {"text": self.text}
        if self.request_contact:
            kwargs["request_contact"] = True
        if self.request_location:
            kwargs["request_location"] = True
        if self.web_app_url:
            kwargs["web_app"] = aiogram.types.WebAppInfo(url=self.web_app_url)
        return kwargs


def reply_markup_builder(
    buttons: list[ReplyButton], adjusting: list[int] = []
) -> aiogram.types.ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    for button in buttons:
        builder.button(**button.to_button_kwargs())
    builder.adjust(*adjusting)
    return builder.as_markup(resize_keyboard=True)


async def reply_markup_builder_from_model(
    buttons, adjusting: list[int] = [], extra_buttons: list[str] = []
) -> aiogram.types.ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    async for button in buttons:  # async iteration over queryset
        builder.button(text=button.text)
    if extra_buttons:
        for text in extra_buttons:
            if text == "Виртуальный помощник":
                builder.button(text=text, web_app=WebAppInfo(url=settings.MINIAPP_URL))
                continue
            builder.button(text=text)
    if adjusting:

        builder.adjust(*adjusting)
    else:
        builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)
