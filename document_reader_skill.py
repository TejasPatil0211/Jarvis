"""
document_reader_skill.py — Read text out of images.

Engines (set OCR_ENGINE in .env):

  auto       Best available that needs no billing account:
             openrouter -> ocrspace -> tesseract -> google
  openrouter Free vision LLM through OpenRouter. Best on handwriting.
             Needs a free OpenRouter account, no credit card.
  ocrspace   OCR.space free API. 25,000 requests/month, no credit card.
             Engine 3 handles handwriting well.
  google     Google Cloud Vision. Excellent, but requires a billing account.
  tesseract  Fully local Tesseract. No key at all, but poor on handwriting.
             Great for printed documents and receipts.
"""

import base64
import glob
import json
import logging
import os
from typing import ClassVar
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

try:  # package context: `python -m jarvis.main`
    from . import config
    from .base import Skill
except ImportError:  # script context: `python main.py`
    import config
    from base import Skill

OCR_TEMP_DIR = config.OCR_TEMP_DIR

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
        "ocr this",
    )

    _IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".heic", ".webp", ".bmp", ".gif")

    def handle(self, user_input: str) -> str:
        image_path = self._extract_path(user_input)
        if not image_path or not os.path.exists(image_path):
            return (
                f"I couldn't find that file. Place images in {OCR_TEMP_DIR}."
            )

        logger.info(f"Document reader matched: {image_path}")

        try:
            text, engine = self._extract_text(image_path)
        except OCRError as e:
            logger.error(f"OCR failed: {e}")
            return f"I couldn't read that document. {e}"

        if not text.strip():
            return "I read the image but found no text in it."

        text = text.strip()
        out_path = self._save_text(image_path, text)
        preview = text if len(text) <= 220 else text[:220].rstrip() + "..."
        return (
            f"Read it using {engine}. {preview} "
            f"Full text saved to {out_path}."
        )

    # ── engine dispatch ─────────────────────────────────────────────────
    def _extract_text(self, image_path: str) -> tuple[str, str]:
        engine = (config.OCR_ENGINE or "auto").strip().lower()
        order = self._engine_order(engine)
        last_error = None

        for name in order:
            try:
                if name == "openrouter":
                    return self._ocr_openrouter(image_path), "OpenRouter vision"
                if name == "ocrspace":
                    return self._ocr_ocrspace(image_path), "OCR.space"
                if name == "google":
                    return self._ocr_google(image_path), "Google Cloud Vision"
                if name == "tesseract":
                    return self._ocr_tesseract(image_path), "Tesseract"
            except OCRError as e:
                logger.warning(f"OCR engine '{name}' failed: {e}")
                last_error = e
                continue

        raise OCRError(
            str(last_error) if last_error else "no OCR engine is available"
        )

    def _engine_order(self, engine: str) -> list[str]:
        if engine == "openrouter":
            return ["openrouter"]
        if engine == "ocrspace":
            return ["ocrspace"]
        if engine == "google":
            return ["google"]
        if engine == "tesseract":
            return ["tesseract"]

        # auto — prefer engines that need no billing account
        order = []
        if config.OPENROUTER_API_KEY:
            order.append("openrouter")
        order.append("ocrspace")
        order.append("tesseract")
        if config.GOOGLE_APPLICATION_CREDENTIALS:
            order.append("google")
        return order

    # ── OpenRouter vision (free, no credit card) ────────────────────────
    def _ocr_openrouter(self, image_path: str) -> str:
        if not config.OPENROUTER_API_KEY:
            raise OCRError("OPENROUTER_API_KEY is not set")

        try:
            from openai import OpenAI
        except ImportError as e:
            raise OCRError("the 'openai' package is not installed") from e

        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        mime = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"

        client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
        )
        try:
            response = client.chat.completions.create(
                model=config.OPENROUTER_VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Transcribe every piece of text in this image "
                                    "exactly as written. If the image contains "
                                    "handwriting, transcribe the handwriting. "
                                    "Return only the transcribed text."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{encoded}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1500,
                temperature=0,
            )
        except Exception as e:
            raise OCRError(f"OpenRouter request failed: {e}") from e

        return (response.choices[0].message.content or "").strip()

    # ── OCR.space (free tier, no credit card) ───────────────────────────
    def _ocr_ocrspace(self, image_path: str) -> str:
        # "helloworld" is OCR.space's public demo key. It works without
        # an account but is rate limited — set OCRSPACE_API_KEY for real use.
        api_key = config.OCRSPACE_API_KEY or "helloworld"
        if not config.OCRSPACE_API_KEY:
            logger.info(
                "OCRSPACE_API_KEY not set — using the public demo key. "
                "Get a free key at https://ocr.space/ocrapi"
            )

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        boundary = "----JarvisBoundary" + os.urandom(8).hex()
        parts = [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="apikey"\r\n\r\n',
            f"{api_key}\r\n".encode(),
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="language"\r\n\r\n',
            b"eng\r\n",
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="OCREngine"\r\n\r\n',
            b"3\r\n",  # Engine 3 — much better on handwriting
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; filename="image.jpg"\r\n',
            b"Content-Type: application/octet-stream\r\n\r\n",
            image_bytes,
            f"\r\n--{boundary}--\r\n".encode(),
        ]

        request = UrlRequest(
            "https://api.ocr.space/parse/image",
            data=b"".join(parts),
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "jarvis",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, OSError, ValueError) as e:
            raise OCRError(f"OCR.space request failed: {e}") from e

        if not payload.get("IsErroredOnProcessing"):
            results = payload.get("ParsedResults") or []
            if results:
                return (results[0].get("ParsedText") or "").strip()

        error = (payload.get("ErrorMessage") or "unknown error").strip()
        raise OCRError(f"OCR.space error: {error[:200]}")

    # ── Google Cloud Vision ─────────────────────────────────────────────
    def _ocr_google(self, image_path: str) -> str:
        creds_path = config.GOOGLE_APPLICATION_CREDENTIALS
        if not creds_path or not os.path.exists(creds_path):
            raise OCRError("GOOGLE_APPLICATION_CREDENTIALS is not set or missing")

        try:
            from google.cloud import vision
        except ImportError as e:
            raise OCRError("google-cloud-vision is not installed") from e

        try:
            client = vision.ImageAnnotatorClient()
            with open(image_path, "rb") as f:
                content = f.read()
            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)
        except Exception as e:
            raise OCRError(f"Google Vision request failed: {e}") from e

        return (response.full_text_annotation.text or "").strip()

    # ── Tesseract (local) ───────────────────────────────────────────────
    def _ocr_tesseract(self, image_path: str) -> str:
        try:
            import pytesseract
        except ImportError as e:
            raise OCRError(
                "pytesseract is not installed (pip install pytesseract). "
                "On Windows also install the Tesseract binary and set "
                "TESSERACT_CMD if it is not on PATH."
            ) from e

        try:
            from PIL import Image
        except ImportError as e:
            raise OCRError("Pillow is not installed") from e

        try:
            image = Image.open(image_path)
            return (pytesseract.image_to_string(image) or "").strip()
        except Exception as e:
            raise OCRError(f"Tesseract failed: {e}") from e

    # ── helpers ─────────────────────────────────────────────────────────
    def _save_text(self, image_path: str, text: str) -> str:
        base = os.path.splitext(os.path.basename(image_path))[0]
        out_dir = os.path.dirname(os.path.abspath(image_path))
        out_path = os.path.join(out_dir, f"{base}.txt")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError as e:
            logger.warning(f"Could not save OCR text: {e}")
            return "(not saved)"
        return out_path

    def _extract_path(self, text: str) -> str | None:
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


class OCRError(RuntimeError):
    """Raised when an OCR backend cannot produce text."""
