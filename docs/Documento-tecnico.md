# Documento técnico

## 🔧 a) Estrategia de desarrollo

### Estructura funcional y técnica

* **Repos/carpetas**

  * `backend/` – API REST con **Django + Django REST Framework (DRF)**.
  * `frontend/` – **Next.js 15 + TypeScript** (App Router), base generada con v0.dev y adaptada.
* **Dominio**

  * **Pelicula** → **Sesion** (fecha/hora, sala, `filas×columnas`) → **Entrada** (asiento y estado).

### Decisiones clave (arquitectura, stack, tooling)

* **Backend**

  * **DRF** para serialización y enrutado; **django-filter** para filtros declarativos.
  * **drf-spectacular** para OpenAPI/Swagger/ReDoc; **corsheaders** para CORS.
  * **Validaciones en dos capas**:

    * **Modelo**: rangos de fila/columna, normalización de `fila`, **unicidad** `(sesion, fila, numero)`, bloqueo de cambios si `PAGADA`.
    * **Serializer**: anticipa errores de rango y traduce conflictos a respuestas claras.
  * **Reglas de negocio**:
    `Entrada` con `estado ∈ {reservada, pagada}`; pago idempotente; propiedades de `Sesion` para capacidad.
  * **Admin Django**: filtros de disponibilidad/ventana temporal/email, inlines, acciones masivas, export CSV, previsualización de póster.
* **API (superficie)**

  * `GET  /api/v1/peliculas/` — búsqueda (`search`) y orden (`ordering`).
  * `GET  /api/v1/sesiones/` — filtros: `pelicula`, `sala`, `inicio_after`, `inicio_before`; búsqueda/orden.
  * `GET  /api/v1/sesiones/{id}/asientos?include=estado` — layout 2D por fila/columna con `libre|reservada|pagada`.
  * `POST /api/v1/entradas/` — **reserva**; conflicto de asiento → **409**.
  * `POST /api/v1/entradas/{id}/pagar/` — **pago idempotente** (200 si ya estaba pagada).
  * `GET  /api/v1/health/` — verificación rápida.
* **Frontend**

  * Páginas: **Cartelera** → **Sesiones** → **Asientos** → **Confirmación**.
  * Cliente HTTP en `frontend/lib/api.ts` (Axios + tipos TS).
  * Estado UI para selección de asientos y tratamiento de errores de concurrencia.
  * **Compra como invitado** (sin registro/login en el flujo de compra).
  * Variables: `NEXT_PUBLIC_API_BASE_URL` (p. ej. `http://127.0.0.1:8000/api/v1` o túnel público).
* **Pruebas**

  * **pytest** con **9 tests E2E**: health, listados/orden/filtros, normalización de `fila`, conflicto **409**, pago idempotente, layout de asientos.

---

## 🧠 b) Estrategia de uso de IA

### Herramientas y fases

* **ChatGPT**

  * Desglose y **priorización** de tareas, checklist y enfoque óptimo.
  * Mejora de **comentarios**, validaciones y organización de código.
  * Ayuda en **resolución de errores** (fixtures, rutas, middlewares, mapeo 400→409).
  * Redacción de **documentación** y prompts de soporte para el front.

* **v0.dev**

  * Generación de **base UI** (páginas, componentes, navegación) y estados del selector de asientos.

* **GitHub Copilot**

  * Autocompletado/snippets en serializers, viewsets, cliente Axios y componentes.

### Justificación del uso

* Reduce tiempo en **boilerplate** y **debug**.
* Aporta **calidad** en validaciones/mensajes y consistencia en la API.
* Agiliza **documentación** y prototipado de UI.

### Pipeline (orden, entradas, salidas, valor añadido)

1. **Ideación** (ChatGPT): entidades, reglas, endpoints → *mapa funcional*.
2. **Diseño UI base** (v0.dev + prompts): páginas/estados → *esqueleto navegable*.
3. **API** (ChatGPT + Copilot): modelos/serializers/views → *superficie coherente con el front*.
4. **Testing** (pytest): casos felices y conflictos → *confianza*.
5. **Documentación** (ChatGPT): documento técnico y README → *alineación del equipo*.
   **Valor añadido**: menor retrabajo, admin operativo, front conectado rápidamente y manejo robusto de conflictos.

---

## 📈 c) Autoevaluación

### Impacto del uso de IA en eficiencia

* **Velocidad**: fuerte reducción en arranque de API/UI y en resolución de bloqueos.
* **Calidad**: validaciones de dominio (modelo+serializer), códigos de error correctos (409), **9 tests** E2E pasando.
* **Entrega**: backend listo y probado; front funcional con **guest checkout**.

### Qué mejoraría en la adopción de IA

* **Prompts reutilizables** para patrones (lista/detalle/formulario, viewsets/serializers).
* **CI** con `ruff/black`, `pytest-cov` y build del front en PRs.
* **Tests de UI** (Vitest + React Testing Library) para el selector de asientos.
* **Trazabilidad** de decisiones asistidas por IA en PRs y **telemetría** de errores de front para iterar UX.