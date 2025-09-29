# --- handlers/tree.py ---------------------------------------------------------
from typing import Optional

from aiogram import types, Bot, Router
from aiogram.enums import ParseMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from telegram.instance.filters.tree_filter import TreeButtonsOnly
from telegram.instance.middlewares import BotClientSessionMiddleWare
from telegram.models.buttonTree import AttachmentData
from telegram_client.models import BotClientSession, BotClient
from telegram.models import ButtonTree
from telegram.instance.markup_buttons import reply_markup_builder_from_model

tree_router = Router()
tree_router.message.outer_middleware(BotClientSessionMiddleWare())

BACK_BTN = "⬅️ Назад"


def back_keyboard() -> ReplyKeyboardMarkup:
    # Minimal keyboard with only the Back button (used on leaves)
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[KeyboardButton(text=BACK_BTN)]],
    )


async def give_parent_tree(message: types.Message, bot: Bot, from_back: bool = False):
    buttons_tree = ButtonTree.objects.filter(parent=None)
    buttons = await reply_markup_builder_from_model(
        buttons_tree,
        extra_buttons=["Виртуальный помощник", "Личный кабинет"],
        adjusting=[2, 2],
    )

    if from_back:
        # When user returns from "Назад", don't show the greeting again
        return await message.answer("Главное меню:", reply_markup=buttons)

    # First entry
    return await message.answer(
        "Готово! Теперь вы можете пользоваться всеми функциями бота.",
        reply_markup=buttons,
        parse_mode=ParseMode.HTML,
    )


async def use_tree(
    message: types.Message,
    bot: Bot,
    session: BotClientSession,
    client: BotClient,
):
    text_in = (message.text or "").strip()

    # 0) Handle BACK at any depth
    if text_in == BACK_BTN:
        # If already at root, just show the root menu again (no greeting)
        if session.current_button is None:
            return await give_parent_tree(message, bot, from_back=True)

        # Move one level up
        parent_id = session.current_button.parent_id
        parent = await ButtonTree.objects.filter(pk=parent_id).afirst()

        session.current_button = parent  # becomes None at root
        await session.asave()

        if parent is None:
            # Now at root
            return await give_parent_tree(message, bot, from_back=True)

        # Show siblings (children of the parent) + Back
        children_qs = parent.children.all()
        buttons = await reply_markup_builder_from_model(
            children_qs,
            extra_buttons=[BACK_BTN],
        )
        return await message.answer(parent.text, reply_markup=buttons)

    # 2) User is at root and selects a top-level node
    if session.current_button is None:
        next_button = (
            await ButtonTree.objects.select_related("attachment")
            .filter(parent=None, text=text_in)
            .afirst()
        )
        if next_button is None:
            return

        children_qs = next_button.children.all()

        # Leaf at root: send attachment (if any) or just text, and show Back to root
        if not await children_qs.aexists():
            if hasattr(next_button, "attachment"):
                return await send_full_attachment(
                    message,
                    next_button.attachment,
                    bot,
                    buttons=back_keyboard(),
                    fallback_text=next_button.text,  # use button text if attachment.text missing
                )
            return await message.answer(next_button.text, reply_markup=back_keyboard())

        # Non-leaf: advance and render children keyboard (+ Back)
        session.current_button = next_button
        await session.asave()

        buttons = await reply_markup_builder_from_model(
            children_qs,
            extra_buttons=[BACK_BTN],
        )

        if hasattr(next_button, "attachment"):
            # ALWAYS send the parent's attachment (if any)...
            await send_full_attachment(
                message,
                next_button.attachment,
                bot,
                buttons=buttons,  # helper may attach markup to text if it sends any
                fallback_text=next_button.text,  # used only if attachment.text is empty
            )
            # ...and THEN ALWAYS show child buttons so user can navigate right away
            return await message.answer(next_button.text, reply_markup=buttons)

        # No attachment → just show node title + children
        return await message.answer(next_button.text, reply_markup=buttons)

    # 3) User is traversing deeper
    if session.current_button is not None:
        next_button = (
            await session.current_button.children.all()
            .select_related("attachment")
            .filter(text=text_in)
            .afirst()
        )
        if next_button is None:
            return

        children_qs = next_button.children.all()

        # Leaf while traversing: send attachment (if any) or text, and show Back
        if not await children_qs.aexists():
            if hasattr(next_button, "attachment"):
                return await send_full_attachment(
                    message,
                    next_button.attachment,
                    bot,
                    buttons=back_keyboard(),
                    fallback_text=next_button.text,
                )
            return await message.answer(next_button.text, reply_markup=back_keyboard())

        # Non-leaf: advance and render children keyboard (+ Back)
        session.current_button = next_button
        await session.asave()

        buttons = await reply_markup_builder_from_model(
            children_qs,
            extra_buttons=[BACK_BTN],
        )
        if hasattr(next_button, "attachment"):
            # ALWAYS send the parent's attachment...
            await send_full_attachment(
                message,
                next_button.attachment,
                bot,
                buttons=buttons,
                fallback_text=next_button.text,
            )
            # ...and THEN ALWAYS show child buttons
            return await message.answer(next_button.text, reply_markup=buttons)

        return await message.answer(next_button.text, reply_markup=buttons)


# Register handler
tree_router.message.register(
    use_tree,
    TreeButtonsOnly(),
    flags={"block": False},  # <— важно!
)


# --- helpers/attachments.py ---------------------------------------------------
from typing import Optional

from aiogram import types
from aiogram.types import FSInputFile
from aiogram.utils.media_group import MediaGroupBuilder
import os

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
TELEGRAM_MEDIA_GROUP_LIMIT = 10  # chunk size (max group size)
TELEGRAM_CAPTION_LIMIT = 1024  # practical caption limit for photo/video
PHOTO_MAX_BYTES = 10 * 1024 * 1024
# NOTE: Telegram requires 2–10 items for media groups. Single item must be sent individually.
# NOTE: Photos > 10 MB cannot be sent with sendPhoto; we fallback to sendDocument.


async def send_full_attachment(
    message: types.Message,
    attachment,
    bot: Bot,
    buttons: Optional[types.ReplyKeyboardMarkup] = None,
    fallback_text: Optional[str] = None,
):
    """
    Sends the attachment linked to a ButtonTree node.

    Text selection:
      - Prefer attachment.text; else fallback_text (button text).

    Caption placement:
      - Put the caption on the *last* item sent (single / group / leftovers).
      - If caption is too long (> TELEGRAM_CAPTION_LIMIT), send it once as a separate message.
    """

    # Choose base text
    att_text = (attachment.text or "").strip()
    base_text = att_text if att_text else (fallback_text or "")
    base_text = base_text.strip()

    def caption_or_none(s: str):
        return s if s and len(s) <= TELEGRAM_CAPTION_LIMIT else None

    # TEXT-only case
    if attachment.source_type == attachment.TEXT:
        if base_text:
            return await message.answer(base_text, reply_markup=buttons)
        return

    # Collect files
    files: list[AttachmentData] = [
        data_item async for data_item in attachment.data.all()
    ]

    # FILE: caption the *last* document if possible; else send text once, then documents
    if attachment.source_type == attachment.FILE:
        cap = caption_or_none(base_text)
        for idx, item in enumerate(files):
            path = item.source.path
            is_last = idx == len(files) - 1
            if is_last and cap:
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=FSInputFile(path),
                    caption=cap,
                )
            else:
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=FSInputFile(path),
                )
        if base_text and not cap:
            await message.answer(base_text, reply_markup=buttons)
        return

    # IMAGE or VIDEO (homogeneous)
    if attachment.source_type in {attachment.IMAGE, attachment.VIDEO}:
        cap = caption_or_none(base_text)
        last_index = len(files) - 1
        for idx, item in enumerate(files):
            path = item.source.path
            media = FSInputFile(path)
            use_caption = (idx == last_index) and (cap is not None)

            if attachment.source_type == attachment.IMAGE:
                # Oversized images → document; caption on last only
                if os.path.getsize(path) > PHOTO_MAX_BYTES:
                    await bot.send_document(
                        chat_id=message.chat.id,
                        document=media,
                        caption=cap if use_caption else None,
                    )
                else:
                    await bot.send_photo(
                        chat_id=message.chat.id,
                        photo=media,
                        caption=cap if use_caption else None,
                    )
            else:
                thumbnail = None
                if item.thumbnail:
                    thumbnail = FSInputFile(item.thumbnail.path)

                await bot.send_video(
                    chat_id=message.chat.id,
                    video=media,
                    thumbnail=thumbnail,
                    caption=cap if use_caption else None,
                )

        if base_text and cap is None:
            await message.answer(base_text, reply_markup=buttons)
        return

    # VIDEO_IMAGE (mixed images/videos)
    if attachment.source_type == attachment.VIDEO_IMAGE:
        if not files:
            if base_text:
                return await message.answer(base_text, reply_markup=buttons)
            return

        # Single file: caption on that (last) file if it fits; handle big photos
        if len(files) == 1:
            single = files[0]
            path = single.source.path
            ext = os.path.splitext(path)[1].lower()
            cap = caption_or_none(base_text)
            media = FSInputFile(path)
            if ext in IMAGE_EXTS:
                if os.path.getsize(path) > PHOTO_MAX_BYTES:
                    await bot.send_document(
                        chat_id=message.chat.id, document=media, caption=cap
                    )
                else:
                    await bot.send_photo(
                        chat_id=message.chat.id, photo=media, caption=cap
                    )
            elif ext in VIDEO_EXTS:
                thumbnail = None
                if item.thumbnail:
                    thumbnail = FSInputFile(single.thumbnail.path)

                await bot.send_video(
                    chat_id=message.chat.id,
                    thumbnail=thumbnail,
                    video=media,
                    caption=cap,
                )
            else:
                await bot.send_document(chat_id=message.chat.id, document=media)

            if base_text and cap is None:
                await message.answer(base_text, reply_markup=buttons)
            return

        # Multiple files: caption on the *global last* item (even if it must be a document)
        caption_value = caption_or_none(base_text)
        caption_available = caption_value is not None
        total = len(files)

        leftovers_paths: list[tuple[str, bool]] = []  # (path, is_global_last)

        for start in range(0, total, TELEGRAM_MEDIA_GROUP_LIMIT):
            chunk = files[start : start + TELEGRAM_MEDIA_GROUP_LIMIT]
            mg = MediaGroupBuilder()

            for i, item in enumerate(chunk):
                path = item.source.path
                ext = os.path.splitext(path)[1].lower()
                global_idx = start + i
                is_global_last = global_idx == total - 1

                use_cap_here = is_global_last and caption_available

                if ext in IMAGE_EXTS:
                    size = os.path.getsize(path)
                    if size > PHOTO_MAX_BYTES:
                        # Too big for photo: send as document (outside the group)
                        await bot.send_document(
                            chat_id=message.chat.id,
                            document=FSInputFile(path),
                            caption=caption_value if use_cap_here else None,
                        )
                        if use_cap_here:
                            caption_available = False
                    else:
                        mg.add_photo(
                            media=FSInputFile(path),
                            caption=caption_value if use_cap_here else None,
                        )
                        if use_cap_here:
                            caption_available = False
                elif ext in VIDEO_EXTS:
                    thumbnail = None
                    if item.thumbnail:
                        thumbnail = FSInputFile(item.thumbnail.path)

                    mg.add_video(
                        media=FSInputFile(path),
                        thumbnail=thumbnail,
                        caption=caption_value if use_cap_here else None,
                    )
                    if use_cap_here:
                        caption_available = False
                else:
                    leftovers_paths.append((path, is_global_last))

            group = mg.build()
            if len(group) >= 2:
                await bot.send_media_group(chat_id=message.chat.id, media=group)
            elif len(group) == 1:
                # Send the single leftover group item directly (no group)
                single = group[0]
                if single.type == "photo":
                    await bot.send_photo(
                        chat_id=message.chat.id,
                        photo=single.media,
                        caption=getattr(single, "caption", None),
                    )
                elif single.type == "video":

                    thumbnail = None
                    if item.thumbnail:
                        thumbnail = FSInputFile(single.thumbnail.path)

                    await bot.send_video(
                        chat_id=message.chat.id,
                        video=single.media,
                        thumbnail=thumbnail,
                        caption=getattr(single, "caption", None),
                    )

        # Send leftovers as documents (in order). If the *very last* file overall is a leftover
        # and caption is still available, put caption on that last leftover.
        for path, is_global_last in leftovers_paths:
            use_cap_here = is_global_last and caption_available
            await bot.send_document(
                chat_id=message.chat.id,
                document=FSInputFile(path),
                caption=caption_value if use_cap_here else None,
            )
            if use_cap_here:
                caption_available = False

        if base_text and caption_value is None:
            await message.answer(base_text, reply_markup=buttons)
        return

    # Fallback: nothing matched — just send text if present
    if base_text:
        await message.answer(base_text, reply_markup=buttons)
