# backend/tests/test_api.py
from __future__ import annotations

from datetime import timedelta
import pytest
from django.utils import timezone
from django.urls import reverse

from cine.models import Pelicula, Sesion, Entrada, TicketStatus


def unwrap_results(payload):
    """Devuelve la lista de resultados independientemente de si hay paginación."""
    return payload["results"] if isinstance(payload, dict) and "results" in payload else payload


@pytest.fixture
def peli_sesion(db):
    """Crea una película y una sesión futura y pequeña para probar asientos."""
    peli = Pelicula.objects.create(
        titulo="Prueba",
        descripcion="demo",
        duracion_min=100,
        clasificacion="TP",
    )
    sesion = Sesion.objects.create(
        pelicula=peli,
        inicio=timezone.now() + timedelta(hours=2),
        sala="Sala 1",
        filas=3,
        columnas=4,
    )
    return peli, sesion


# -----------------------
# Health
# -----------------------
@pytest.mark.django_db
def test_health_ok(api):
    r = api.get("/api/v1/health/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# -----------------------
# Películas
# -----------------------
@pytest.mark.django_db
def test_listar_peliculas_busqueda_y_orden(api):
    Pelicula.objects.create(titulo="AAAA", duracion_min=120, clasificacion="TP")
    Pelicula.objects.create(titulo="BBBB", duracion_min=90, clasificacion="+7")

    # búsqueda por título
    url = reverse("peliculas-list")
    r = api.get(url, {"search": "AAA"})
    assert r.status_code == 200
    data = unwrap_results(r.json())
    assert any(p["titulo"] == "AAAA" for p in data)

    # orden descendente por duración
    r2 = api.get(url, {"ordering": "-duracion_min"})
    d2 = unwrap_results(r2.json())
    assert d2[0]["duracion_min"] >= d2[1]["duracion_min"]


@pytest.mark.django_db
def test_crear_pelicula_requiere_auth(api):
    url = reverse("peliculas-list")
    r = api.post(url, {"titulo": "Nueva", "duracion_min": 100, "clasificacion": "TP"}, format="json")
    # IsAuthenticatedOrReadOnly → sin credenciales -> 401
    assert r.status_code in (401, 403)  # según configuración de auth, normalmente 401


@pytest.mark.django_db
def test_crear_pelicula_ok(api_auth):
    url = reverse("peliculas-list")
    r = api_auth.post(url, {"titulo": "Nueva", "duracion_min": 100, "clasificacion": "TP"}, format="json")
    assert r.status_code == 201
    body = r.json()
    assert body["id"] and body["titulo"] == "Nueva"


# -----------------------
# Sesiones
# -----------------------
@pytest.mark.django_db
def test_sesion_asientos_estado(api, api_auth, peli_sesion):
    _, sesion = peli_sesion

    # Creamos dos entradas por API: una reservada, otra que luego pagamos
    crear_url = reverse("entradas-list")
    r1 = api_auth.post(
        crear_url,
        {"sesion": sesion.id, "fila": "B", "numero": 2, "email": "a@ex.com", "estado": "reservada"},
        format="json",
    )
    assert r1.status_code == 201
    r2 = api_auth.post(
        crear_url,
        {"sesion": sesion.id, "fila": "B", "numero": 3, "email": "b@ex.com", "estado": "reservada"},
        format="json",
    )
    assert r2.status_code == 201
    entrada_b3 = r2.json()

    # Pagar B3
    pagar_url = reverse("entradas-pagar", args=[entrada_b3["id"]])
    rp = api_auth.post(pagar_url, {})
    assert rp.status_code == 200
    assert rp.json()["estado"] == "pagada"

    # Consultar layout con estado
    asientos_url = reverse("sesiones-asientos", args=[sesion.id])
    rl = api.get(asientos_url, {"include": "estado"})
    assert rl.status_code == 200
    layout = rl.json()["layout"]
    # B2 → reservada, B3 → pagada
    fila_b = next(f for f in layout if f[0]["fila"] == "B")
    estado_b2 = next(c for c in fila_b if c["numero"] == 2)["estado"]
    estado_b3 = next(c for c in fila_b if c["numero"] == 3)["estado"]
    assert estado_b2 == "reservada"
    assert estado_b3 == "pagada"


@pytest.mark.django_db
def test_sesion_filters_por_rango(api, peli_sesion):
    _, sesion = peli_sesion
    # Otra sesión fuera del rango
    Sesion.objects.create(
        pelicula=sesion.pelicula,
        inicio=sesion.inicio + timedelta(days=3),
        sala="Sala 2",
        filas=3,
        columnas=4,
    )
    url = reverse("sesiones-list")
    r = api.get(url, {"inicio_after": (sesion.inicio - timedelta(minutes=1)).isoformat()})
    assert r.status_code == 200
    data = unwrap_results(r.json())
    # Debe incluir la sesión base
    assert any(x["id"] == sesion.id for x in data)


# -----------------------
# Entradas
# -----------------------
@pytest.mark.django_db
def test_reservar_asiento_conflicto_409(api_auth, peli_sesion):
    _, sesion = peli_sesion
    url = reverse("entradas-list")

    ok = api_auth.post(url, {"sesion": sesion.id, "fila": "A", "numero": 1}, format="json")
    assert ok.status_code == 201

    dup = api_auth.post(url, {"sesion": sesion.id, "fila": "A", "numero": 1}, format="json")
    assert dup.status_code == 409
    assert "Asiento" in dup.json()["detail"] or "asiento" in dup.json()["detail"]


@pytest.mark.django_db
def test_entrada_normaliza_fila(api_auth, peli_sesion):
    _, sesion = peli_sesion
    url = reverse("entradas-list")
    r = api_auth.post(
    url, {"sesion": sesion.id, "fila": "b", "numero": 4, "email": "x@y.com"},
    format="json",
)
    assert r.status_code == 201
    body = r.json()
    assert body["fila"] == "B"
    assert body["etiqueta_asiento"] == "B4"


@pytest.mark.django_db
def test_pagar_idempotente(api_auth, peli_sesion):
    _, sesion = peli_sesion
    # Creamos como reservada
    e = api_auth.post(
        reverse("entradas-list"),
        {"sesion": sesion.id, "fila": "C", "numero": 1, "email": "p@p.com"},
        format="json",
    ).json()

    # Pagar dos veces → siempre 200 y estado pagada
    url = reverse("entradas-pagar", args=[e["id"]])
    r1 = api_auth.post(url, {})
    r2 = api_auth.post(url, {})
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["estado"] == r2.json()["estado"] == "pagada"
