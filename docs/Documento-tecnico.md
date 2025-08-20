# Documento técnico (Fullstack + IA)

## 🔧 a) Estrategia de desarrollo

### Cómo estructuré el proyecto (funcional y técnico)

**Dominio y reglas**

* **Entidades**: `Pelicula`, `Sesion`, `Entrada`.
* **Reglas clave**:

  * Unicidad de asiento por sesión (constraint `(sesion, fila, numero)`).
  * Validación de rangos de butacas: `fila` (A–Z, dentro de `filas`) y `numero` (1..`columnas`).
  * Cálculo de capacidad por sesión: `asientos_totales`, `asientos_disponibles`.

**API REST (Django + DRF)**

* **Versionado**: prefijo `/api/v1`.
* **Permisos**: `IsAuthenticatedOrReadOnly` (lectura pública; escritura con usuario).
* **Películas**

  * `GET/POST /peliculas/`, `GET/PUT/PATCH/DELETE /peliculas/{id}/`
  * Búsqueda (`?search=titulo`) y orden (`?ordering=titulo|-duracion_min`).
  * Serializer con `clasificacion_display`.
* **Sesiones**

  * `GET/POST /sesiones/`, `GET/PUT/PATCH/DELETE /sesiones/{id}/`
  * Filtros (`django-filter`): `pelicula`, `sala`, `inicio_after`, `inicio_before`.
  * Búsqueda (`pelicula__titulo`, `sala`) y orden (`inicio`, `sala`).
  * Métricas anotadas en queryset: `reservadas`, `pagadas` sin N+1.
  * **Mapa de asientos**: `GET /sesiones/{id}/asientos/`

    * `?include=estado` → `libre | reservada | pagada`.
    * Sin parámetro → `ocupado: true|false`.
* **Entradas**

  * `GET/POST /entradas/`, `GET/DELETE /entradas/{id}/`
  * Filtros: `sesion`, `estado`, `email` (icontains), `creada_after`, `creada_before`.
  * **Pago**: `POST /entradas/{id}/pagar` (idempotente).
  * Manejo de conflictos de asiento: mapeo de `IntegrityError` a **409**.

**Validaciones y errores**

* Validación de dominio en `Entrada.clean()` (rango fila/columna) y normalización a mayúsculas en `save()`.
* `ModelCleanErrorMixin` en serializers: transforma `DjangoValidationError` en 400 coherentes de DRF.
* Colisiones de unicidad: 409 (cuando la BD dispara la constraint).

**Administración (Django Admin)**

* **Película**: listado con `titulo`, `duracion_min`, `clasificacion` y preview de `poster_url`.
* **Sesión**: columnas calculadas (`Disponibles`, `Reservadas`, `Pagadas`), filtros de **disponibilidad** y **proximidad** temporal, inline de entradas y **export CSV** de entradas por sesiones seleccionadas.
* **Entrada**: acciones masivas (marcar **pagadas**/**reservadas**), export CSV, enlace mailto, y fields de butaca en read-only si está **pagada**.

**Observabilidad y DX**

* **Health**: `GET /api/v1/health/`.
* **OpenAPI**: `/api/schema/`; **Swagger** `/api/docs/`; **ReDoc** `/api/redoc/`.
* **CORS** para desarrollo; Debug Toolbar en `DEBUG`.
* **Fixtures** cargadas (películas, sesiones, entradas): *Installed 3374 object(s) from 3 fixture(s)*.

**Pruebas**

* `pytest`/`pytest-django` con 9 pruebas E2E:

  * Health; películas (búsqueda, orden, creación requiere auth);
  * sesiones (filtros rango y layout con `include=estado`);
  * entradas (creación, duplicado 409, normalización de `fila`, pago idempotente).
* `conftest.py`: hash MD5, email en memoria, JSON por defecto, clientes `api` y `api_auth`.

**Decisiones clave (arquitectura, stack, herramientas)**

* **Django + DRF** para productividad, ecosistema y admin nativo.
* **`django-filter`** para filtros declarativos y consistentes.
* **`drf-spectacular`** para esquema OpenAPI y UIs de documentación listas.
* **Constraints + transacciones** para garantizar consistencia (unicidad de butaca; `atomic` en crear/pagar).
* **Anotaciones** de queryset para métricas y evitar N+1.
* **Tests E2E** para validar el comportamiento observable de la API.

---

## 🧠 b) Estrategia de uso de IA

### Herramientas utilizadas y fases

* **ChatGPT**

  * Desglose de tareas y **priorización**; elaboración de la **checklist** por fases.
  * Propuesta de **arquitectura** (modelos, endpoints, permisos, validaciones).
  * **Mejora de comentarios** y organización del código.
  * **Resolución de errores** (fixtures y orden de carga, conflicto con `format_suffix_patterns` en URLs, orden de `MIDDLEWARE` con Debug Toolbar, manejo de 400/409).
  * Redacción de **documentación técnica** y guías de prueba.
* **v0 (gratuito)**

  * Preparación del **frontend**: estructura de páginas y componentes; guía para el **prompt** de UI (navegación, estados de asiento, loaders, manejo de errores).
* **GitHub Copilot**

  * **Autocompletado** para servicios Axios, hooks y esqueletos de componentes, agilizando codificación del front.

### Justificación del uso

* **Velocidad** en exploración y montaje de piezas repetitivas.
* **Calidad** en validaciones, mensajes de error y documentación.
* **Fiabilidad** apoyada en pruebas E2E que verifican los flujos clave.

### Pipeline de uso de IA (orden, entradas, salidas, valor añadido)

1. **Ideación (ChatGPT)**

   * **Entrada**: requisitos del reto y objetivos.
   * **Salida**: checklist priorizada, modelo de dominio, rutas iniciales.
   * **Valor**: claridad del alcance y plan de ejecución.
2. **Diseño de UI (v0 + ChatGPT)**

   * **Entrada**: flujos (cartelera → sesiones → asientos → confirmación) y restricciones.
   * **Salida**: estructura de páginas/componentes y **prompt** de UI afinado.
   * **Valor**: reducir iteraciones al arrancar el front.
3. **Generación de API/código (ChatGPT + Copilot)**

   * **Entrada**: arquitectura decidida y contratos de datos.
   * **Salida**: serializers con mixin de errores, viewsets con filtros/acciones, admin con filtros/CSV, servicios de front.
   * **Valor**: mayor productividad manteniendo consistencia.
4. **Testing (ChatGPT para casos)**

   * **Entrada**: flujos críticos (reserva, duplicado, pago, filtros).
   * **Salida**: 9 tests E2E en `pytest`.
   * **Valor**: confianza en regresiones y en el manejo de conflictos.
5. **Documentación (ChatGPT)**

   * **Entrada**: código final y endpoints.
   * **Salida**: este documento y guía de uso de la API.
   * **Valor**: transferencia clara del estado del proyecto.

---

**Nota de estado**: backend implementado y probado con documentación, admin y fixtures listos; el frontend se abordará con la estructura y prompts definidos en el pipeline.
