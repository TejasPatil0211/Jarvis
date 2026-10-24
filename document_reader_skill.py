import glob
import logging
import os
from typing import ClassVar

from base import Skill
from config import OCR_TEMP_DIR

logger = logging.getLogger(__name__)

class DocumentReaderSkill(Skill):
    name = "document_reader"
    keywords: ClassVar[tuple[str, ...]] = (
        "read this",
        "read the document",
        "read this document",
        "what does this say",
        "transcribe this",
        "scan this",
        "read my notes",
        "read my handwriting",
    )

    _IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".heic", ".webp")

    def handle(self, user_input: str) -> str:
        image_path = self._extract_path(user_input)
        if not image_path or not os.path.exists(image_path):
            return (
                f"I couldn't find that file. Place handwritten"
                f"images in {OCR_TEMP_DIR}."
            )

        logger.info(f"Document reader matched: {image_path}")
        return (
            f"I found {os.path.basename(image_path)} but OCR"
            f"isn't wired up yet. See BUGS_FOUND.md"
        )

    def _extract_path(self, text: str) -> str:
        for ext in self._IMAGE_EXTS:
            for word in text.split():
                if word.lower().endswith(ext):
                    return word
        if os.path.exists(OCR_TEMP_DIR):
            files = glob.glob(os.path.join(OCR_TEMP_DIR, "*"))
            images = [f for f in files if f.lower().endswith(self._IMAGE_EXTS)]
            if images:
                return max(images, key=os.path.getmtime)
            return None


