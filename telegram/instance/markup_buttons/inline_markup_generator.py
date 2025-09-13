import pydantic
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional, Union
from aiogram.types import WebAppInfo
from aiogram.filters.callback_data import CallbackData


class InlineButton(pydantic.BaseModel):
    text: str
    url: Optional[str] = None
    callback_data: Optional[Union[str, CallbackData]] = None
    web_app_url: Optional[str] = None

    def to_button_kwargs(self) -> dict:
        """Return only the set kwargs for aiogram's builder.button."""
        kwargs = {"text": self.text}
        if self.url:
            kwargs["url"] = self.url

        if self.web_app_url:
            kwargs["web_app"] = WebAppInfo(url=self.web_app_url)
        else:
            if self.callback_data:

                kwargs["callback_data"] = self.callback_data
            else:

                kwargs["callback_data"] = self.text
        return kwargs


def inline_markup_builder(
    buttons: list[InlineButton], adjusting: list[int] = []
) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()

    for button in buttons:
        builder.button(**button.to_button_kwargs())
    builder.adjust(*adjusting)
    return builder.as_markup(resize_keyboard=True)
