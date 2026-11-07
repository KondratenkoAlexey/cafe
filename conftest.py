import sys

import pytest

# Не создавать __pycache__ при прогоне тестов в дереве проекта.
sys.dont_write_bytecode = True


@pytest.fixture(autouse=True)
def _locmem_cache(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "cafe-tests",
            "KEY_PREFIX": "cafe",
        }
    }
