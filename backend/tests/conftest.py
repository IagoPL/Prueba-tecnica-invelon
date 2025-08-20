# backend/tests/conftest.py
from __future__ import annotations

from typing import Callable

import pytest
from django.urls import reverse as dj_reverse
from rest_framework.test import APIClient


# ----------------------------
# Ajustes globales para tests
# ----------------------------
@pytest.fixture(autouse=True)
def _fast_test_settings(settings):
    """
    Optimiza velocidad y evita efectos colaterales en test.
    - Hash de contraseñas barato (MD5).
    - Sin validadores de contraseña.
    - Email en memoria.
    - DRF: peticiones de prueba en JSON por defecto.
    """
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.AUTH_PASSWORD_VALIDATORS = []
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    rf = getattr(settings, "REST_FRAMEWORK", {}).copy()
    rf["TEST_REQUEST_DEFAULT_FORMAT"] = "json"
    settings.REST_FRAMEWORK = rf


# ----------------------------
# Helpers de cliente
# ----------------------------
def _make_api_client() -> APIClient:
    client = APIClient()
    client.default_format = "json"  # DRF APIClient respeta este valor
    client.credentials(HTTP_ACCEPT="application/json")
    return client


@pytest.fixture
def api() -> APIClient:
    """Cliente anónimo (ideal para GET)."""
    return _make_api_client()


@pytest.fixture
def password() -> str:
    """Password por defecto para usuarios de test."""
    return "pass12345"


@pytest.fixture
def user(db, django_user_model, password):
    """Usuario normal persistido en DB."""
    return django_user_model.objects.create_user(username="tester", password=password)


@pytest.fixture
def user_factory(db, django_user_model, password) -> Callable[..., object]:
    """
    Factory para crear usuarios arbitrarios en tests:
        u = user_factory(username="ana", is_staff=True)
    """
    def create(**kwargs):
        defaults = {"username": "tester2", "password": password}
        defaults.update(kwargs)
        # Si no se pasa password, usa el por defecto
        pwd = defaults.pop("password", password)
        user_obj = django_user_model.objects.create_user(**defaults)
        if pwd != password:
            # create_user ya setea el password si se pasó; esto es por si vino en kwargs
            user_obj.set_password(pwd)
            user_obj.save(update_fields=["password"])
        return user_obj
    return create


@pytest.fixture
def api_auth(db, user) -> APIClient:
    """
    Cliente autenticado con `user` (ideal para POST/acciones).
    Usa DRF `force_authenticate`, que evita el login real y es más rápido.
    """
    client = _make_api_client()
    client.force_authenticate(user=user)
    return client


# ----------------------------
# Utilidades de URLs
# ----------------------------
@pytest.fixture
def reverse() -> Callable[..., str]:
    """
    Atajo para `django.urls.reverse` en tests:
        url = reverse("v1:peliculas-list")
        url = reverse("v1:sesiones-detail", args=[pk])
    """
    return dj_reverse
