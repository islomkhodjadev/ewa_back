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
import logging

logger = logging.getLogger(__name__)

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
    logger.info("HERE IN GIVE TREE START")
    buttons_tree = ButtonTree.objects.filter(parent=None)
    buttons = await reply_markup_builder_from_model(
        buttons_tree,
        extra_buttons=[
            "Подобрать БАД - тест",
            "Виртуальный помощник",
            "Личный кабинет",
        ],
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
        return await message.answer(
            parent.text, reply_markup=buttons, parse_mode=ParseMode.HTML
        )

    # 1) User is at root and selects a top-level node
    if session.current_button is None:
        next_button = (
            await ButtonTree.objects.select_related("attachment")
            .filter(parent=None, text=text_in)  # Explicitly check parent=None
            .afirst()
        )
        if next_button is None:
            # Button not found at root level
            logger.warning(f"Button '{text_in}' not found at root level")
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
                    fallback_text=next_button.text,
                )
            return await message.answer(
                next_button.text,
                reply_markup=back_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        # Non-leaf: advance and render children keyboard (+ Back)
        session.current_button = next_button
        await session.asave()

        buttons = await reply_markup_builder_from_model(
            children_qs,
            extra_buttons=[BACK_BTN],
        )

        if hasattr(next_button, "attachment"):
            await send_full_attachment(
                message,
                next_button.attachment,
                bot,
                buttons=buttons,
                fallback_text=next_button.text,
            )
            return await message.answer(
                next_button.text,
                reply_markup=buttons,
                parse_mode=ParseMode.HTML,
            )

        return await message.answer(
            next_button.text,
            reply_markup=buttons,
            parse_mode=ParseMode.HTML,
        )

    # 2) User is traversing deeper - FIXED VERSION
    if session.current_button is not None:
        # Get ALL potential next buttons with this name
        # In section 2) User is traversing deeper:
        potential_buttons = [
            button
            async for button in session.current_button.children.all()
            .select_related("attachment")
            .filter(text=text_in)
        ]

        if not potential_buttons:
            # Button not found among children
            logger.warning(
                f"Button '{text_in}' not found among children of '{session.current_button.text}'"
            )
            return

        # If multiple buttons with same name exist, take the first one
        # You might want to add additional logic here if needed
        next_button = potential_buttons[0]

        # Additional safety check - verify parent relationship
        if next_button.parent_id != session.current_button.id:
            logger.error(f"Parent-child relationship mismatch for button '{text_in}'")
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
            return await message.answer(
                next_button.text,
                reply_markup=back_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        # Non-leaf: advance and render children keyboard (+ Back)
        session.current_button = next_button
        await session.asave()

        buttons = await reply_markup_builder_from_model(
            children_qs,
            extra_buttons=[BACK_BTN],
        )

        if hasattr(next_button, "attachment"):
            await send_full_attachment(
                message,
                next_button.attachment,
                bot,
                buttons=buttons,
                fallback_text=next_button.text,
            )
            return await message.answer(
                next_button.text,
                reply_markup=buttons,
                parse_mode=ParseMode.HTML,
            )

        return await message.answer(
            next_button.text,
            reply_markup=buttons,
            parse_mode=ParseMode.HTML,
        )


# Register handler
tree_router.message.register(
    use_tree,
    TreeButtonsOnly(),
    flags={"block": False},  # <— важно!
)


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def is_text_too_long_for_caption(text: str) -> bool:
    """Check if text exceeds Telegram caption limit."""
    return len(text) > 1024


def can_use_media_group(media_count: int) -> bool:
    """Check if we can use media group (2-10 items)."""
    return 2 <= media_count <= 10


# --- helpers/attachments.py ---------------------------------------------------
from typing import Optional

from aiogram import types
from aiogram.types import FSInputFile
from aiogram.utils.media_group import MediaGroupBuilder
import os

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
FILE_EXTS = set()  # All other extensions are considered files
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
    Sends the attachment linked to a ButtonTree node with proper text and media limits.
    """

    # Choose base text
    att_text = (attachment.text or "").strip()
    base_text = att_text if att_text else (fallback_text or "")
    base_text = base_text.strip()

    def split_long_text(text: str, max_length: int = 4096) -> list[str]:
        """Split text into chunks that don't exceed max_length."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        while text:
            if len(text) <= max_length:
                chunks.append(text)
                break
            # Find the last space within the limit
            split_pos = text.rfind(" ", 0, max_length)
            if split_pos == -1:
                # No spaces found, force split
                split_pos = max_length
            chunks.append(text[:split_pos])
            text = text[split_pos:].strip()
        return chunks

    def get_caption_for_media(text: str) -> Optional[str]:
        """Get caption for media (max 1024 chars) or None if too long."""
        return text if text and len(text) <= 1024 else None

    # TEXT-only case
    if attachment.source_type == attachment.TEXT:
        if base_text:
            text_chunks = split_long_text(base_text)
            for i, chunk in enumerate(text_chunks):
                is_last = i == len(text_chunks) - 1
                await message.answer(
                    chunk,
                    reply_markup=buttons if is_last else None,
                    parse_mode=ParseMode.HTML,
                )
        elif buttons:
            # If no text but we have buttons, just send buttons
            await message.answer("Выберите действие:", reply_markup=buttons)
        return

    # Collect files
    files: list[AttachmentData] = [
        data_item async for data_item in attachment.data.all()
    ]

    # FILE: send documents with proper caption handling
    if attachment.source_type == attachment.FILE:
        # Send text first if it's too long for caption
        text_chunks = split_long_text(base_text)
        media_caption = get_caption_for_media(base_text)

        # If text is too long for caption, send it as separate messages first
        text_sent_separately = False
        if media_caption is None and base_text:
            for chunk in text_chunks:
                await message.answer(chunk, parse_mode=ParseMode.HTML)
            media_caption = None  # Don't use caption after sending text separately
            text_sent_separately = True

        # Send documents
        for idx, item in enumerate(files):
            path = item.source.path
            is_last = idx == len(files) - 1
            caption = media_caption if is_last and media_caption else None

            await bot.send_document(
                chat_id=message.chat.id,
                document=FSInputFile(path),
                caption=caption,
                parse_mode=ParseMode.HTML if caption else None,
            )

        # Send buttons at the end if we have them
        if buttons:
            # Only send additional message if text was sent separately or we have files
            if text_sent_separately or files:
                await message.answer("Выберите действие:", reply_markup=buttons)
            else:
                # No text and no files, just send buttons with minimal message
                await message.answer("Выберите действие:", reply_markup=buttons)
        return

    # VIDEO_IMAGE_FILE: mixed media types
    if attachment.source_type == attachment.VIDEO_IMAGE_FILE:
        if not files:
            if base_text:
                text_chunks = split_long_text(base_text)
                for i, chunk in enumerate(text_chunks):
                    is_last = i == len(text_chunks) - 1
                    await message.answer(
                        chunk,
                        reply_markup=buttons if is_last else None,
                        parse_mode=ParseMode.HTML,
                    )
            elif buttons:
                await message.answer("Выберите действие:", reply_markup=buttons)
            return

        # Separate files from media
        file_items = []
        media_items = []

        for item in files:
            path = item.source.path
            ext = os.path.splitext(path)[1].lower()
            if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
                media_items.append(item)
            else:
                file_items.append(item)

        # Handle text - send long text first
        text_chunks = split_long_text(base_text)
        media_caption = get_caption_for_media(base_text)

        # Track if we sent text separately
        text_sent_separately = False
        if media_caption is None and base_text:
            for chunk in text_chunks:
                await message.answer(chunk, parse_mode=ParseMode.HTML)
            text_sent_separately = True

        # Step 1: Send all files first
        if file_items:
            for item in file_items:
                path = item.source.path
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=FSInputFile(path),
                )

        # Step 2: Send media items as media groups (max 10 per group)
        media_was_sent = False
        if media_items:
            total_media = len(media_items)
            caption_used = False
            media_was_sent = True

            for start in range(0, total_media, TELEGRAM_MEDIA_GROUP_LIMIT):
                chunk = media_items[start : start + TELEGRAM_MEDIA_GROUP_LIMIT]
                mg = MediaGroupBuilder()

                for i, item in enumerate(chunk):
                    path = item.source.path
                    ext = os.path.splitext(path)[1].lower()
                    is_global_last = start + i == total_media - 1

                    # Use caption only on the last item of the last chunk
                    caption_text = (
                        media_caption
                        if is_global_last and media_caption and not caption_used
                        else None
                    )
                    if caption_text:
                        caption_used = True

                    if ext in IMAGE_EXTS:
                        size = os.path.getsize(path)
                        if size > PHOTO_MAX_BYTES:
                            # Too big for photo: send as document
                            await bot.send_document(
                                chat_id=message.chat.id,
                                document=FSInputFile(path),
                                caption=caption_text,
                                parse_mode=ParseMode.HTML if caption_text else None,
                            )
                        else:
                            mg.add_photo(
                                media=FSInputFile(path),
                                caption=caption_text,
                            )
                    elif ext in VIDEO_EXTS:
                        thumbnail = None
                        if item.thumbnail:
                            thumbnail = FSInputFile(item.thumbnail.path)

                        mg.add_video(
                            media=FSInputFile(path),
                            thumbnail=thumbnail,
                            caption=caption_text,
                        )

                # Send media group if we have at least 2 items, otherwise send individually
                media_group = mg.build()
                if len(media_group) >= 2:
                    await bot.send_media_group(
                        chat_id=message.chat.id, media=media_group
                    )
                elif len(media_group) == 1:
                    single_media = media_group[0]
                    if single_media.type == "photo":
                        await bot.send_photo(
                            chat_id=message.chat.id,
                            photo=single_media.media,
                            caption=single_media.caption,
                            parse_mode=ParseMode.HTML if single_media.caption else None,
                        )
                    elif single_media.type == "video":
                        # Find the corresponding item for thumbnail
                        item_idx = start
                        if item_idx < len(media_items):
                            current_item = media_items[item_idx]
                            thumbnail = None
                            if current_item.thumbnail:
                                thumbnail = FSInputFile(current_item.thumbnail.path)

                        await bot.send_video(
                            chat_id=message.chat.id,
                            video=single_media.media,
                            thumbnail=thumbnail,
                            caption=single_media.caption,
                            parse_mode=ParseMode.HTML if single_media.caption else None,
                        )

        # Send buttons at the end only if we actually sent content
        if buttons and (text_sent_separately or file_items or media_was_sent):
            await message.answer("Выберите действие:", reply_markup=buttons)
        elif buttons:
            # No content was sent, just show buttons with minimal message
            await message.answer("Выберите действие:", reply_markup=buttons)
        return

    # IMAGE or VIDEO (homogeneous media)
    if attachment.source_type in {attachment.IMAGE, attachment.VIDEO}:
        if not files:
            if base_text:
                text_chunks = split_long_text(base_text)
                for i, chunk in enumerate(text_chunks):
                    is_last = i == len(text_chunks) - 1
                    await message.answer(
                        chunk,
                        reply_markup=buttons if is_last else None,
                        parse_mode=ParseMode.HTML,
                    )
            elif buttons:
                await message.answer("Выберите действие:", reply_markup=buttons)
            return

        text_chunks = split_long_text(base_text)
        media_caption = get_caption_for_media(base_text)

        # Track if text was sent separately
        text_sent_separately = False
        if media_caption is None and base_text:
            for chunk in text_chunks:
                await message.answer(chunk, parse_mode=ParseMode.HTML)
            text_sent_separately = True

        # Send media in groups
        total_files = len(files)
        caption_used = False
        media_was_sent = False

        for start in range(0, total_files, TELEGRAM_MEDIA_GROUP_LIMIT):
            chunk = files[start : start + TELEGRAM_MEDIA_GROUP_LIMIT]
            media_was_sent = True

            # For homogeneous media, we can use media groups more efficiently
            if len(chunk) > 1:
                mg = MediaGroupBuilder()
                for i, item in enumerate(chunk):
                    path = item.source.path
                    is_global_last = start + i == total_files - 1
                    caption_text = (
                        media_caption
                        if is_global_last and media_caption and not caption_used
                        else None
                    )

                    if caption_text:
                        caption_used = True

                    if attachment.source_type == attachment.IMAGE:
                        mg.add_photo(
                            media=FSInputFile(path),
                            caption=caption_text,
                        )
                    else:  # VIDEO
                        thumbnail = None
                        if item.thumbnail:
                            thumbnail = FSInputFile(item.thumbnail.path)
                        mg.add_video(
                            media=FSInputFile(path),
                            thumbnail=thumbnail,
                            caption=caption_text,
                        )

                await bot.send_media_group(chat_id=message.chat.id, media=mg.build())
            else:
                # Single item
                item = chunk[0]
                path = item.source.path
                is_global_last = start == total_files - 1
                caption_text = (
                    media_caption
                    if is_global_last and media_caption and not caption_used
                    else None
                )

                if caption_text:
                    caption_used = True

                if attachment.source_type == attachment.IMAGE:
                    await bot.send_photo(
                        chat_id=message.chat.id,
                        photo=FSInputFile(path),
                        caption=caption_text,
                        parse_mode=ParseMode.HTML if caption_text else None,
                    )
                else:  # VIDEO
                    thumbnail = None
                    if item.thumbnail:
                        thumbnail = FSInputFile(item.thumbnail.path)
                    await bot.send_video(
                        chat_id=message.chat.id,
                        video=FSInputFile(path),
                        thumbnail=thumbnail,
                        caption=caption_text,
                        parse_mode=ParseMode.HTML if caption_text else None,
                    )

        # Send buttons only if content was actually sent
        if buttons and (text_sent_separately or media_was_sent):
            await message.answer("Выберите действие:", reply_markup=buttons)
        elif buttons:
            await message.answer("Выберите действие:", reply_markup=buttons)
        return

    # VIDEO_IMAGE (mixed) - similar to VIDEO_IMAGE_FILE but with different logic
    if attachment.source_type == attachment.VIDEO_IMAGE:
        # Use the same logic as VIDEO_IMAGE_FILE since they're similar
        await send_full_attachment(
            message,
            attachment,
            bot,
            buttons,
            fallback_text,
        )
        return

    # Fallback for unhandled types
    if base_text:
        text_chunks = split_long_text(base_text)
        for i, chunk in enumerate(text_chunks):
            is_last = i == len(text_chunks) - 1
            await message.answer(
                chunk,
                reply_markup=buttons if is_last else None,
                parse_mode=ParseMode.HTML,
            )
    elif buttons:
        await message.answer("Выберите действие:", reply_markup=buttons)
