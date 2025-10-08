# --- handlers/tree.py ---------------------------------------------------------
from typing import Optional

from aiogram import types, Bot, Router
from aiogram.enums import ParseMode, ChatAction
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from telegram.instance.filters.tree_filter import TreeButtonsOnly
from telegram.instance.middlewares import BotClientSessionMiddleWare
from telegram.models.buttonTree import AttachmentData, AttachmentToButton
from telegram_client.models import BotClientSession, BotClient
from telegram.models import ButtonTree
from telegram.instance.markup_buttons import reply_markup_builder_from_model
import logging
import re
import os
import asyncio

logger = logging.getLogger(__name__)

tree_router = Router()
tree_router.message.outer_middleware(BotClientSessionMiddleWare())

BACK_BTN = "⬅️ Назад"

# Pre-compile patterns for maximum speed
_VALID_TAGS_PATTERN = re.compile(
    r"</?(b|strong|i|em|u|ins|s|strike|del|code|pre|a|tg-spoiler|tg-emoji)[^>]*>"
)
_PROBLEMATIC_LT_PATTERN = re.compile(
    r"<(?![a-z/])"
)  # Match < not followed by letter or /


def safe_telegram_html(text: str) -> str:
    """
    Ultra-fast HTML sanitizer that preserves ONLY Telegram-allowed HTML tags
    and escapes everything else that could break parsing.
    """
    if not text:
        return text

    # Replace all < that are not part of valid Telegram HTML tags
    def escape_invalid_lt(match):
        return "&lt;"

    # First escape all problematic < characters
    safe_text = _PROBLEMATIC_LT_PATTERN.sub(escape_invalid_lt, text)

    return safe_text


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
        try:
            client_session = await BotClientSession.objects.filter(
                client__chat_id=message.from_user.id
            ).aupdate(current_button=None)

        # When user returns from "Назад", don't show the greeting again
        except Exception as e:
            logger.info(e)
        return await message.answer("Главное меню:", reply_markup=buttons)

    # First entry
    return await message.answer(
        safe_telegram_html(
            "Готово! Теперь вы можете пользоваться всеми функциями бота."
        ),
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
            safe_telegram_html(parent.text),
            reply_markup=buttons,
            parse_mode=ParseMode.HTML,
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
        has_children = await children_qs.aexists()
        has_attachment = hasattr(next_button, "attachment")

        # Leaf at root: send attachment (if any) or just text, and show Back to root
        if not has_children:
            if has_attachment:
                return await send_full_attachment(
                    message,
                    next_button.attachment,
                    bot,
                    buttons=back_keyboard(),
                    fallback_text=None,  # Don't send button name
                )
            # No attachment, just send the text with back button
            return await message.answer(
                safe_telegram_html(next_button.text),
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

        # Only send the button text if there's no attachment
        if not has_attachment:
            return await message.answer(
                safe_telegram_html(next_button.text),
                reply_markup=buttons,
                parse_mode=ParseMode.HTML,
            )

        # If there's an attachment, send it with the buttons - don't send button text separately
        return await send_full_attachment(
            message,
            next_button.attachment,
            bot,
            buttons=buttons,
            fallback_text=None,  # Don't send button name
        )

    # 2) User is traversing deeper
    if session.current_button is not None:
        # Get ALL potential next buttons with this name
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
        next_button = potential_buttons[0]

        # Additional safety check - verify parent relationship
        if next_button.parent_id != session.current_button.id:
            logger.error(f"Parent-child relationship mismatch for button '{text_in}'")
            return

        children_qs = next_button.children.all()
        has_children = await children_qs.aexists()
        has_attachment = hasattr(next_button, "attachment")

        # Leaf while traversing: send attachment (if any) or text, and show Back
        if not has_children:
            if has_attachment:
                return await send_full_attachment(
                    message,
                    next_button.attachment,
                    bot,
                    buttons=back_keyboard(),
                    fallback_text=None,  # Don't send button name
                )
            # No attachment, just send the text with back button
            return await message.answer(
                safe_telegram_html(next_button.text),
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

        # Only send the button text if there's no attachment
        if not has_attachment:
            return await message.answer(
                safe_telegram_html(next_button.text),
                reply_markup=buttons,
                parse_mode=ParseMode.HTML,
            )

        # If there's an attachment, send it with the buttons - don't send button text separately
        return await send_full_attachment(
            message,
            next_button.attachment,
            bot,
            buttons=buttons,
            fallback_text=None,  # Don't send button name
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

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
FILE_EXTS = set()  # All other extensions are considered files
TELEGRAM_MEDIA_GROUP_LIMIT = 10  # chunk size (max group size)
TELEGRAM_CAPTION_LIMIT = 1024  # practical caption limit for photo/video
PHOTO_MAX_BYTES = 10 * 1024 * 1024
# NOTE: Telegram requires 2–10 items for media groups. Single item must be sent individually.
# NOTE: Photos > 10 MB cannot be sent with sendPhoto; we fallback to sendDocument.


async def send_chat_action_periodically(chat_id: int, bot: Bot, action: ChatAction):
    """Keep sending chat action until cancelled."""
    while True:
        try:
            await bot.send_chat_action(chat_id=chat_id, action=action)
            await asyncio.sleep(5)  # Telegram requires action every 5 seconds
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error sending chat action: {e}")
            break


async def send_full_attachment(
    message: types.Message,
    attachment,  # This is AttachmentToButton instance
    bot: Bot,
    buttons: Optional[types.ReplyKeyboardMarkup] = None,
    fallback_text: Optional[str] = None,
):
    """
    Sends the attachment linked to a ButtonTree node with proper text and media limits.
    Handles all edge cases including mixed media, large files, and errors.
    """
    chat_action_task = None

    try:
        # Choose base text and make it safe - ONLY use attachment text, never button name
        att_text = (attachment.text or "").strip()
        base_text = att_text if att_text else ""
        base_text = safe_telegram_html(base_text.strip())

        def split_long_text(text: str, max_length: int = 4096) -> list[str]:
            """Split text into chunks that don't exceed max_length."""
            if len(text) <= max_length:
                return [text]
            chunks = []
            while text:
                if len(text) <= max_length:
                    chunks.append(text)
                    break
                split_pos = text.rfind(" ", 0, max_length)
                if split_pos == -1:
                    split_pos = max_length
                chunks.append(text[:split_pos])
                text = text[split_pos:].strip()
            return chunks

        def get_caption_for_media(text: str) -> Optional[str]:
            """Get caption for media only if text exists and fits limit."""
            return safe_telegram_html(text) if text and len(text) <= 1024 else None

        # TEXT-only case
        if attachment.source_type == AttachmentToButton.TEXT:
            if base_text:
                text_chunks = split_long_text(base_text)
                for i, chunk in enumerate(text_chunks):
                    is_last = i == len(text_chunks) - 1
                    await message.answer(
                        chunk,
                        reply_markup=buttons if is_last else None,
                        parse_mode=ParseMode.HTML,
                    )

            return

        # Collect files with error handling
        files: list[AttachmentData] = []
        try:
            # Correct way to get related files
            files = [data_item async for data_item in attachment.data.all()]
        except Exception as e:
            logger.error(f"Error loading files for attachment {attachment.id}: {e}")
            await message.answer(
                "Ошибка загрузки файлов. Пожалуйста, попробуйте позже."
            )
            return

        if not files:
            # No files case
            if base_text:
                text_chunks = split_long_text(base_text)
                for i, chunk in enumerate(text_chunks):
                    is_last = i == len(text_chunks) - 1
                    await message.answer(
                        chunk,
                        reply_markup=buttons if is_last else None,
                        parse_mode=ParseMode.HTML,
                    )
            return

        # Start chat action (typing/uploading) in background
        chat_action_task = asyncio.create_task(
            send_chat_action_periodically(
                chat_id=message.chat.id,
                bot=bot,
                action=(
                    ChatAction.UPLOAD_DOCUMENT
                    if any(
                        f
                        for f in files
                        if not f.source.name.lower().endswith(
                            (".jpg", ".jpeg", ".png", ".gif", ".webp")
                        )
                    )
                    else ChatAction.UPLOAD_PHOTO
                ),
            )
        )

        # Helper function to validate and prepare file
        async def prepare_file(attachment_data: AttachmentData) -> Optional[dict]:
            """Validate file and return file info or None if invalid."""
            try:
                # Correct way to access file path in Django
                if not attachment_data.source:
                    logger.warning(
                        f"No file attached to AttachmentData {attachment_data.id}"
                    )
                    return None

                path = attachment_data.source.path

                # Check if file exists and is accessible
                if not os.path.exists(path):
                    logger.warning(f"File not found: {path}")
                    return None

                # Check file size
                file_size = os.path.getsize(path)
                if file_size == 0:
                    logger.warning(f"Empty file: {path}")
                    return None

                # Check file permissions
                if not os.access(path, os.R_OK):
                    logger.warning(f"No read permissions for file: {path}")
                    return None

                ext = os.path.splitext(attachment_data.source.name)[1].lower()

                return {
                    "attachment_data": attachment_data,
                    "path": path,
                    "ext": ext,
                    "size": file_size,
                    "type": (
                        "image"
                        if ext in IMAGE_EXTS
                        else "video" if ext in VIDEO_EXTS else "document"
                    ),
                    "filename": os.path.basename(attachment_data.source.name),
                }
            except Exception as e:
                logger.error(
                    f"Error preparing file {getattr(attachment_data, 'source', 'unknown')}: {e}"
                )
                return None

        # Helper function to send media groups by type
        async def send_media_groups_by_type(
            valid_files: list[dict], caption_text: Optional[str] = None
        ):
            """Send media files grouped by type (photos together, videos together)."""
            if not valid_files:
                return

            # Separate files by type
            photos = [
                f
                for f in valid_files
                if f["type"] == "image" and f["size"] <= PHOTO_MAX_BYTES
            ]
            videos = [f for f in valid_files if f["type"] == "video"]
            documents = [
                f
                for f in valid_files
                if f["type"] == "document"
                or (f["type"] == "image" and f["size"] > PHOTO_MAX_BYTES)
            ]

            sent_count = 0
            total_files = len(valid_files)
            caption_used = False

            # Send photos as media groups
            for start in range(0, len(photos), TELEGRAM_MEDIA_GROUP_LIMIT):
                chunk = photos[start : start + TELEGRAM_MEDIA_GROUP_LIMIT]
                if len(chunk) > 1:
                    mg = MediaGroupBuilder()
                    for i, file_info in enumerate(chunk):
                        is_last = sent_count + i == total_files - 1
                        current_caption = (
                            caption_text
                            if is_last and caption_text and not caption_used
                            else None
                        )
                        if current_caption:
                            caption_used = True

                        mg.add_photo(
                            media=FSInputFile(file_info["path"]),
                            caption=current_caption,
                        )

                    try:
                        await bot.send_media_group(
                            chat_id=message.chat.id, media=mg.build()
                        )
                        sent_count += len(chunk)
                    except Exception as e:
                        logger.error(f"Error sending photo group: {e}")
                        # Fallback: send individually
                        for file_info in chunk:
                            await send_single_file(
                                file_info,
                                (
                                    caption_text
                                    if sent_count == total_files - 1
                                    and not caption_used
                                    else None
                                ),
                            )
                            sent_count += 1
                else:
                    for file_info in chunk:
                        is_last = sent_count == total_files - 1
                        await send_single_file(
                            file_info,
                            caption_text if is_last and not caption_used else None,
                        )
                        if is_last and caption_text:
                            caption_used = True
                        sent_count += 1

            # Send videos as media groups (separate from photos)
            for start in range(0, len(videos), TELEGRAM_MEDIA_GROUP_LIMIT):
                chunk = videos[start : start + TELEGRAM_MEDIA_GROUP_LIMIT]
                if len(chunk) > 1:
                    mg = MediaGroupBuilder()
                    for i, file_info in enumerate(chunk):
                        is_last = sent_count + i == total_files - 1
                        current_caption = (
                            caption_text
                            if is_last and caption_text and not caption_used
                            else None
                        )
                        if current_caption:
                            caption_used = True

                        thumbnail = None
                        if file_info["attachment_data"].thumbnail:
                            try:
                                thumbnail_path = file_info[
                                    "attachment_data"
                                ].thumbnail.path
                                if os.path.exists(thumbnail_path):
                                    thumbnail = FSInputFile(thumbnail_path)
                            except Exception as e:
                                logger.warning(
                                    f"Could not load thumbnail for {file_info['filename']}: {e}"
                                )

                        mg.add_video(
                            media=FSInputFile(file_info["path"]),
                            thumbnail=thumbnail,
                            caption=current_caption,
                        )

                    try:
                        await bot.send_media_group(
                            chat_id=message.chat.id, media=mg.build()
                        )
                        sent_count += len(chunk)
                    except Exception as e:
                        logger.error(f"Error sending video group: {e}")
                        # Fallback: send individually
                        for file_info in chunk:
                            await send_single_file(
                                file_info,
                                (
                                    caption_text
                                    if sent_count == total_files - 1
                                    and not caption_used
                                    else None
                                ),
                            )
                            sent_count += 1
                else:
                    for file_info in chunk:
                        is_last = sent_count == total_files - 1
                        await send_single_file(
                            file_info,
                            caption_text if is_last and not caption_used else None,
                        )
                        if is_last and caption_text:
                            caption_used = True
                        sent_count += 1

            # Send documents individually (can't be grouped)
            for file_info in documents:
                is_last = sent_count == total_files - 1
                await send_single_file(
                    file_info, caption_text if is_last and not caption_used else None
                )
                if is_last and caption_text:
                    caption_used = True
                sent_count += 1

        # Helper function to send single file
        async def send_single_file(file_info: dict, caption: Optional[str] = None):
            """Send a single file with proper method based on type and size."""
            try:
                if (
                    file_info["type"] == "image"
                    and file_info["size"] <= PHOTO_MAX_BYTES
                ):
                    await bot.send_photo(
                        chat_id=message.chat.id,
                        photo=FSInputFile(file_info["path"]),
                        caption=caption,
                        parse_mode=ParseMode.HTML if caption else None,
                    )
                elif file_info["type"] == "video":
                    thumbnail = None
                    if file_info["attachment_data"].thumbnail:
                        try:
                            thumbnail_path = file_info["attachment_data"].thumbnail.path
                            if os.path.exists(thumbnail_path):
                                thumbnail = FSInputFile(thumbnail_path)
                        except Exception as e:
                            logger.warning(
                                f"Could not load thumbnail for {file_info['filename']}: {e}"
                            )

                    await bot.send_video(
                        chat_id=message.chat.id,
                        video=FSInputFile(file_info["path"]),
                        thumbnail=thumbnail,
                        caption=caption,
                        parse_mode=ParseMode.HTML if caption else None,
                    )
                else:
                    # Document or large image
                    await bot.send_document(
                        chat_id=message.chat.id,
                        document=FSInputFile(file_info["path"]),
                        caption=caption,
                        parse_mode=ParseMode.HTML if caption else None,
                    )
            except Exception as e:
                logger.error(f"Error sending file {file_info['path']}: {e}")
                await message.answer(
                    f"Ошибка отправки файла. Файл: {file_info['filename']}"
                )

        # Handle text first for all media types
        text_chunks = split_long_text(base_text)
        media_caption = get_caption_for_media(base_text)

        text_sent_separately = False
        if base_text:
            # Send typing action for text
            await bot.send_chat_action(
                chat_id=message.chat.id, action=ChatAction.TYPING
            )
            await asyncio.sleep(1)  # Small delay to show typing

            for chunk in text_chunks:
                await message.answer(chunk, parse_mode=ParseMode.HTML)
            media_caption = None  # Don't use caption after sending text separately
            text_sent_separately = True

        # Prepare and validate all files
        valid_files = []
        for attachment_data in files:
            file_info = await prepare_file(attachment_data)
            if file_info:
                valid_files.append(file_info)
            else:
                logger.warning(
                    f"Skipping invalid file: {getattr(attachment_data, 'source', 'unknown')}"
                )

        if not valid_files:
            if chat_action_task:
                chat_action_task.cancel()
            await message.answer("Нет доступных файлов для отправки.")
            return

        # Send all valid files
        await send_media_groups_by_type(valid_files, media_caption)

        # Stop chat action
        if chat_action_task:
            chat_action_task.cancel()

    except Exception as e:
        logger.error(f"Unexpected error in send_full_attachment: {e}", exc_info=True)
        # Stop chat action on error
        if chat_action_task:
            chat_action_task.cancel()
        await message.answer("Произошла непредвиденная ошибка при отправке материалов.")
        if buttons:
            await message.answer("Выберите действие:", reply_markup=buttons)
