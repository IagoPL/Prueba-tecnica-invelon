from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class AgeRating(models.TextChoices):
    """Clasificación por edades estándar en España."""
    TP = "TP", _("Todos los públicos")
    MAS_7 = "+7", _("Mayores de 7")
    MAS_12 = "+12", _("Mayores de 12")
    MAS_16 = "+16", _("Mayores de 16")
    MAS_18 = "+18", _("Mayores de 18")


class TicketStatus(models.TextChoices):
    """Estados de una entrada."""
    RESERVADA = "reservada", _("reservada")
    PAGADA = "pagada", _("pagada")


class Pelicula(models.Model):
    """
    Película proyectada en el cine.

    Contiene metadatos básicos y un posible póster para mostrar en la UI.
    """

    titulo = models.CharField(
        max_length=200,
        verbose_name=_("título"),
        help_text=_("Título oficial de la película."),
        db_index=True,
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name=_("descripción"),
        help_text=_("Sinopsis o notas adicionales."),
    )
    duracion_min = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("duración (min)"),
        help_text=_("Duración total en minutos (≥ 1)."),
    )
    clasificacion = models.CharField(  # ← corregido el typo
        max_length=4,
        choices=AgeRating.choices,
        blank=True,
        verbose_name=_("clasificación por edades"),
        help_text=_("Por ejemplo: TP, +7, +12, +16, +18."),
    )
    poster_url = models.URLField(
        blank=True,
        verbose_name=_("URL del póster"),
        help_text=_("Enlace a la imagen del póster (opcional)."),
    )

    class Meta:
        verbose_name = _("película")
        verbose_name_plural = _("películas")
        ordering = ["titulo"]

    def __str__(self) -> str:
        return self.titulo


class Sesion(models.Model):
    """
    Proyección de una película en una sala, fecha y hora concretas.

    Define la cuadrícula de asientos mediante número de filas y columnas.
    """

    pelicula = models.ForeignKey(
        Pelicula,
        on_delete=models.CASCADE,
        related_name="sesiones",
        verbose_name=_("película"),
    )
    inicio = models.DateTimeField(
        verbose_name=_("inicio"),
        help_text=_("Fecha y hora de inicio de la sesión."),
        db_index=True,
    )
    sala = models.CharField(
        max_length=20,
        default="Sala 1",
        verbose_name=_("sala"),
        help_text=_("Nombre o identificador de la sala."),
    )
    filas = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        verbose_name=_("nº de filas"),
        help_text=_("Cantidad de filas (p. ej., 10 → A-J). Debe ser ≥ 1."),
    )
    columnas = models.PositiveSmallIntegerField(
        default=12,
        validators=[MinValueValidator(1)],
        verbose_name=_("nº de columnas"),
        help_text=_("Asientos por fila (p. ej., 12 → 1-12). Debe ser ≥ 1."),
    )

    class Meta:
        verbose_name = _("sesión")
        verbose_name_plural = _("sesiones")
        ordering = ["inicio"]
        indexes = [
            models.Index(fields=["pelicula", "inicio"], name="sesion_pelicula_inicio_idx"),
        ]
        constraints = [
            # Evita dos sesiones de la misma película en la misma sala y hora (útil en muchos cines)
            models.UniqueConstraint(
                fields=["inicio", "sala"],
                name="unique_sesion_sala_fecha",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.pelicula.titulo} @ {self.inicio:%Y-%m-%d %H:%M}"

    # --- Utilidades de capacidad ---
    @property
    def asientos_totales(self) -> int:
        """Cantidad total de asientos disponibles en la sala para esta sesión."""
        return int(self.filas) * int(self.columnas)

    @property
    def asientos_vendidos_o_reservados(self) -> int:
        """Entradas ya registradas (reservadas o pagadas)."""
        return self.entradas.count()

    @property
    def asientos_disponibles(self) -> int:
        """Asientos aún libres según las entradas creadas."""
        return self.asientos_totales - self.asientos_vendidos_o_reservados


class Entrada(models.Model):
    """
    Entrada (asiento) asociado a una sesión concreta.

    La unicidad (sesión, fila, número) evita la doble venta del mismo asiento.
    """

    sesion = models.ForeignKey(
        Sesion,
        on_delete=models.CASCADE,
        related_name="entradas",
        verbose_name=_("sesión"),
    )
    fila = models.CharField(
        max_length=1,
        verbose_name=_("fila"),
        help_text=_("Letra de la fila (A, B, C, ...)."),
        validators=[RegexValidator(regex=r"^[A-Za-z]$", message=_("Debe ser una única letra."))],
    )
    numero = models.PositiveSmallIntegerField(
        verbose_name=_("número"),
        help_text=_("Número de asiento dentro de la fila (≥ 1)."),
        validators=[MinValueValidator(1)],
    )
    email = models.EmailField(
        blank=True,
        verbose_name=_("email del comprador"),
        help_text=_("Correo electrónico asociado (opcional)."),
        db_index=True,
    )
    estado = models.CharField(
        max_length=12,
        choices=TicketStatus.choices,
        default=TicketStatus.RESERVADA,
        verbose_name=_("estado"),
    )
    creada_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("creada en"),
    )

    class Meta:
        verbose_name = _("entrada")
        verbose_name_plural = _("entradas")
        ordering = ["-creada_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["sesion", "fila", "numero"],
                name="unique_asiento_por_sesion",
            ),
        ]
        indexes = [
            models.Index(fields=["sesion", "estado"], name="entrada_sesion_estado_idx"),
        ]

    # --- Validaciones de dominio ---
    def clean(self) -> None:
        """
        Valida que:
        - `fila` sea una letra válida dentro del rango de la sesión (A..).
        - `numero` esté dentro del rango [1..columnas] de la sesión.
        """
        super().clean()

        if not self.sesion_id:
            # Si no hay sesión aún, no podemos validar rangos específicos
            return

        # Normalizamos la fila a mayúsculas para evitar colisiones (a == A).
        if self.fila:
            self.fila = self.fila.upper()

        # Rango de filas permitido según la sesión (A..).
        max_fila_index = int(self.sesion.filas)  # 1 → A, 2 → A-B, etc.
        if not self.fila or len(self.fila) != 1 or not ("A" <= self.fila <= "Z"):
            raise ValidationError({"fila": _("La fila debe ser una única letra A-Z.")})

        fila_index = (ord(self.fila) - ord("A")) + 1
        if fila_index < 1 or fila_index > max_fila_index:
            raise ValidationError(
                {"fila": _(f"La fila {self.fila} no existe para esta sesión (máx: {max_fila_index}).")}
            )

        # Validación dinámica del número de asiento
        max_columnas = int(self.sesion.columnas)
        if self.numero < 1 or self.numero > max_columnas:
            raise ValidationError(
                {"numero": _(f"El asiento debe estar entre 1 y {max_columnas} para esta sesión.")}
            )

    def save(self, *args, **kwargs):
        """
        Llama a `full_clean()` antes de guardar para asegurar validaciones de negocio,
        especialmente los rangos de fila/columna dependientes de la sesión.
        """
        self.full_clean()
        return super().save(*args, **kwargs)

    # --- Presentación ---
    @property
    def etiqueta_asiento(self) -> str:
        """Etiqueta amigable del asiento, p. ej. 'B7'."""
        return f"{self.fila}{self.numero}"

    def __str__(self) -> str:
        return f"{self.sesion} - {self.etiqueta_asiento}"
