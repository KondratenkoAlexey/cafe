import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import User
from service.models import CafeSettings
from service.qrcode_utils import get_qr_payload, set_qr_payload


pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="qr-admin",
        password="pass",
        role=User.Role.ADMIN,
        is_staff=True,
    )


def test_default_qr_payload_from_settings(settings):
    settings.PUBLIC_BASE_URL = "http://192.168.1.85/"
    CafeSettings.objects.all().delete()
    assert get_qr_payload() == "http://192.168.1.85/"


def test_saved_qr_payload_overrides_default(settings):
    settings.PUBLIC_BASE_URL = "http://192.168.1.104/"
    set_qr_payload("http://192.168.1.85/")
    assert get_qr_payload() == "http://192.168.1.85/"


def test_staff_can_save_and_render_qr(admin_user):
    client = Client()
    client.force_login(admin_user)
    response = client.post(
        reverse("staff_qr_save"),
        {"qr_payload": "http://192.168.1.85/"},
    )
    assert response.status_code == 302
    assert CafeSettings.load().qr_payload == "http://192.168.1.85/"

    page = client.get(reverse("staff_qr"))
    assert page.status_code == 200
    assert b"192.168.1.85" in page.content

    image = client.get(reverse("staff_qr_image"))
    assert image.status_code == 200
    assert image["Content-Type"] == "image/png"
    assert image.content[:8] == b"\x89PNG\r\n\x1a\n"
