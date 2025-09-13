from django.db import models
from django.core.exceptions import ValidationError
import os


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
    choices = [
        (TEXT, "Текст"),
        (FILE, "Файл"),
        (VIDEO, "Видео"),
        (IMAGE, "Изображение"),
        (VIDEO_IMAGE, "Видео или изображение"),
    ]
    source_type = models.CharField(
        max_length=15,
        choices=choices,
        default=TEXT,
        verbose_name="Тип источника",
    )

    class Meta:
        verbose_name = "📎 Вложение к кнопке"
        verbose_name_plural = "📎 Вложения к кнопкам"

    def __str__(self):
        return f"Вложение для кнопки: {self.button.text}"


class AttachmentData(models.Model):
    source = models.FileField(upload_to="tree-buttons/leaf-data", verbose_name="Файл")
    attachment = models.ForeignKey(
        AttachmentToButton,
        on_delete=models.CASCADE,
        related_name="data",
        verbose_name="Вложение",
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

    def __str__(self):
        return f"Файл для {self.attachment}"
