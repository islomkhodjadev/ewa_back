from django.db import models
from django.core.exceptions import ValidationError
import os
from PIL import Image


class ButtonTree(models.Model):
    text = models.CharField(max_length=255, verbose_name="Текст кнопки")
    parent = models.ForeignKey(
        "ButtonTree",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
        verbose_name="Родительская кнопка",
    )

    class Meta:
        verbose_name = "🔘 Кнопка"
        verbose_name_plural = "🔘 Дерево кнопок"

    def __str__(self) -> str:
        return self.text

    def is_root(self):
        return self.parent is None

    def is_leaf(self):
        return not self.children.exists()


class AttachmentToButton(models.Model):
    button = models.OneToOneField(
        ButtonTree,
        on_delete=models.CASCADE,
        related_name="attachment",
        verbose_name="Кнопка",
    )
    text = models.TextField(verbose_name="Текст вложения")
    TEXT = "text"
    FILE = "file"
    VIDEO = "video"
    IMAGE = "image"
    VIDEO_IMAGE = "video_image"
    VIDEO_IMAGE_FILE = "video_image_file"
    choices = [
        (TEXT, "Текст"),
        (FILE, "Файл"),
        (VIDEO, "Видео"),
        (IMAGE, "Изображение"),
        (VIDEO_IMAGE, "Видео или изображение"),
        (VIDEO_IMAGE_FILE, "Видео, изображение, файл "),
    ]
    source_type = models.CharField(
        max_length=16,
        choices=choices,
        default=TEXT,
        verbose_name="Тип источника",
    )

    class Meta:
        verbose_name = "📎 Вложение к кнопке"
        verbose_name_plural = "📎 Вложения к кнопкам"

    def __str__(self):
        return f"Вложение для кнопки: {self.button.text}"


def validate_thumbnail(value):
    """
    Custom validator function for thumbnail images
    Validates:
    - Format must be JPEG
    - Size must be less than 200 kB
    - Dimensions must not exceed 320x320 pixels
    """
    if not value:
        return

    # Size check (200 kB = 200 * 1024 bytes)
    if value.size > 200 * 1024:
        raise ValidationError("Размер миниатюры не должен превышать 200 kB.")

    # Format check by extension
    if not value.name.lower().endswith((".jpg", ".jpeg")):
        raise ValidationError("Миниатюра должна быть в формате JPEG (.jpg или .jpeg).")

    # Dimension and format check using PIL
    try:
        with Image.open(value) as img:
            width, height = img.size
            if width > 320 or height > 320:
                raise ValidationError(
                    "Размеры миниатюры не должны превышать 320x320 пикселей."
                )

            # Check if image is actually JPEG format
            if img.format not in ["JPEG", "JFIF"]:
                raise ValidationError("Миниатюра должна быть в формате JPEG.")

    except Exception as e:
        raise ValidationError(f"Не удалось прочитать изображение: {str(e)}")


class AttachmentData(models.Model):
    source = models.FileField(upload_to="tree-buttons/leaf-data", verbose_name="Файл")
    attachment = models.ForeignKey(
        AttachmentToButton,
        on_delete=models.CASCADE,
        related_name="data",
        verbose_name="Вложение",
    )
    thumbnail = models.ImageField(
        verbose_name="изображение видеофайла",
        null=True,
        blank=True,
        upload_to="thumbnails/",
        help_text="Формат: JPEG, макс. размер: 200 kB, макс. размеры: 320x320px",
        validators=[validate_thumbnail],  # Use function instead of class
    )

    class Meta:
        verbose_name = "📂 Данные вложения"
        verbose_name_plural = "📂 Файлы вложений"

    def clean(self):
        stype = self.attachment.source_type
        ext = os.path.splitext(self.source.name)[1].lower() if self.source else ""

        image_exts = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        video_exts = [".mp4", ".mov", ".avi", ".mkv", ".webm"]

        if stype == AttachmentToButton.TEXT:
            raise ValidationError("Для текстового вложения нельзя загружать файлы.")

        if stype == AttachmentToButton.IMAGE and ext not in image_exts:
            raise ValidationError(
                f"Недопустимый формат изображения '{ext}'. Разрешено: {', '.join(image_exts)}"
            )

        if stype == AttachmentToButton.VIDEO and ext not in video_exts:
            raise ValidationError(
                f"Недопустимый формат видео '{ext}'. Разрешено: {', '.join(video_exts)}"
            )

        if (
            stype == AttachmentToButton.VIDEO_IMAGE
            and ext not in video_exts + image_exts
        ):
            raise ValidationError(
                f"Недопустимый формат '{ext}'. Разрешено: {', '.join(video_exts + image_exts)}"
            )

        if stype == AttachmentToButton.FILE and not ext:
            raise ValidationError("Необходимо загрузить файл для типа 'Файл'.")

        if stype == AttachmentToButton.VIDEO_IMAGE_FILE and not ext:
            raise ValidationError(
                "Необходимо загрузить файл для типа 'Видео, изображение, файл'."
            )

    def save(self, *args, **kwargs):
        """Override save to ensure validation runs everywhere"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Файл для {self.attachment}"
