"""Генерация QR-кода для входа на сайт."""

from io import BytesIO
from urllib.parse import urlparse

import qrcode
from django.conf import settings

from .models import CafeSettings

QR_PRESETS = (
    ("http://192.168.1.85/", "192.168.1.85"),
    ("http://192.168.1.104/", "192.168.1.104"),
    ("http://localhost/", "localhost"),
)


def default_qr_payload() -> str:
    configured = getattr(settings, "PUBLIC_BASE_URL", "") or ""
    configured = configured.strip()
    if configured:
        return configured if configured.endswith("/") else f"{configured}/"
    return "http://192.168.1.104/"


def get_qr_payload() -> str:
    cafe = CafeSettings.load()
    payload = (cafe.qr_payload or "").strip()
    return payload or default_qr_payload()


def normalize_qr_payload(raw: str) -> str:
    payload = (raw or "").strip()
    if not payload:
        raise ValueError("Укажите текст для QR-кода.")
    if len(payload) > 500:
        raise ValueError("Слишком длинный текст (максимум 500 символов).")
    parsed = urlparse(payload)
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise ValueError("Некорректный адрес: укажите хост, например http://192.168.1.85/")
    return payload


def set_qr_payload(raw: str) -> str:
    payload = normalize_qr_payload(raw)
    cafe = CafeSettings.load()
    cafe.qr_payload = payload
    cafe.save(update_fields=["qr_payload", "updated_at"])
    return payload


def build_qr_png(payload: str | None = None, *, box_size: int = 10, border: int = 2) -> bytes:
    text = (payload or get_qr_payload()).strip()
    if not text:
        text = default_qr_payload()
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
