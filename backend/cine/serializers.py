from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import Pelicula, Sesion, Entrada, TicketStatus


# =========================
# Mixin: convierte ValidationError del modelo en errores DRF (400)
# =========================
class ModelCleanErrorMixin:
    """
    Envuelve create/update para capturar DjangoValidationError (del model.full_clean/save)
    y transformarlo en serializers.ValidationError (HTTP 400).
    """
    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as e:
            detail = getattr(e, "message_dict", None) or {"non_field_errors": e.messages}
            raise serializers.ValidationError(detail)

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as e:
            detail = getattr(e, "message_dict", None) or {"non_field_errors": e.messages}
            raise serializers.ValidationError(detail)


# =========================
# Película
# =========================
class PeliculaSerializer(ModelCleanErrorMixin, serializers.ModelSerializer):
    """
    Serializer de películas con el display human-readable de la clasificación.
    """
    clasificacion_display = serializers.CharField(
        source="get_clasificacion_display", read_only=True
    )

    class Meta:
        model = Pelicula
        fields = (
            "id",
            "titulo",
            "descripcion",
            "duracion_min",
            "clasificacion",
            "clasificacion_display",
            "poster_url",
        )
        read_only_fields = ("id",)


# =========================
# Sesión
# =========================
class SesionSerializer(ModelCleanErrorMixin, serializers.ModelSerializer):
    """
    Serializer de sesiones.
    - `pelicula` anidada (solo lectura) + `pelicula_id` para escritura.
    - Totales/disponibles provienen de propiedades del modelo.
    - `reservadas` y `pagadas` intentan usar anotaciones del queryset; si no hay,
      calculan con COUNT (útil para detalle).
    """
    pelicula = PeliculaSerializer(read_only=True)
    pelicula_id = serializers.PrimaryKeyRelatedField(
        queryset=Pelicula.objects.all(),
        source="pelicula",
        write_only=True,
        help_text="ID de la película a proyectar.",
    )
    asientos_totales = serializers.IntegerField(read_only=True)
    asientos_disponibles = serializers.IntegerField(read_only=True)

    # Contadores opcionales (mira get_queryset del Admin como ejemplo de anotación)
    reservadas = serializers.SerializerMethodField()
    pagadas = serializers.SerializerMethodField()

    class Meta:
        model = Sesion
        fields = (
            "id",
            "pelicula",
            "pelicula_id",
            "inicio",
            "sala",
            "filas",
            "columnas",
            "asientos_totales",
            "asientos_disponibles",
            "reservadas",
            "pagadas",
        )
        read_only_fields = ("id", "asientos_totales", "asientos_disponibles", "reservadas", "pagadas")

    def get_reservadas(self, obj: Sesion) -> int:
        # Si la vista anotó reservadas_count, la usamos; si no, COUNT directo.
        return getattr(obj, "reservadas_count", obj.entradas.filter(estado=TicketStatus.RESERVADA).count())

    def get_pagadas(self, obj: Sesion) -> int:
        return getattr(obj, "pagadas_count", obj.entradas.filter(estado=TicketStatus.PAGADA).count())


# =========================
# Entrada
# =========================
class EntradaSerializer(ModelCleanErrorMixin, serializers.ModelSerializer):
    """
    Serializer de entradas con validaciones amigables:
    - Normaliza `fila` a mayúscula.
    - Valida (temprano) que el asiento exista dentro de la cuadrícula de la sesión.
      (El modelo ya valida; aquí damos error 400 antes y con mejor mensaje.)
    - Evita asientos duplicados vía UniqueTogetherValidator.
    - Protege asientos si la entrada está pagada (no se pueden mover).
    """
    etiqueta_asiento = serializers.CharField(read_only=True)

    class Meta:
        model = Entrada
        fields = ("id", "sesion", "fila", "numero", "email", "estado", "creada_en", "etiqueta_asiento")
        read_only_fields = ("id", "creada_en", "etiqueta_asiento")
        validators = [
            UniqueTogetherValidator(
                queryset=Entrada.objects.all(),
                fields=("sesion", "fila", "numero"),
                message="Ese asiento ya está reservado o pagado para esa sesión.",
            )
        ]

    # Normaliza la letra de la fila
    def validate_fila(self, value: str) -> str:
        return value.upper() if value else value

    def validate(self, attrs):
        """
        Valida que fila/numero existen en la sesión.
        """
        sesion = attrs.get("sesion") or getattr(self.instance, "sesion", None)
        fila = attrs.get("fila") or getattr(self.instance, "fila", None)
        numero = attrs.get("numero") or getattr(self.instance, "numero", None)

        # Solo validamos si tenemos los 3 valores
        if sesion and fila and numero:
            fila = fila.upper()
            # A-Z simple
            if len(fila) != 1 or not ("A" <= fila <= "Z"):
                raise serializers.ValidationError({"fila": "La fila debe ser una única letra A-Z."})

            max_filas = int(sesion.filas)
            index = (ord(fila) - ord("A")) + 1
            if index < 1 or index > max_filas:
                raise serializers.ValidationError({"fila": f"La fila {fila} no existe en esta sesión (máx: {max_filas})."})

            max_cols = int(sesion.columnas)
            if int(numero) < 1 or int(numero) > max_cols:
                raise serializers.ValidationError({"numero": f"El asiento debe estar entre 1 y {max_cols}."})

            # Reescribimos la fila normalizada
            attrs["fila"] = fila

        return attrs

    def update(self, instance: Entrada, validated_data):
        """
        Bloquea cambios de asiento/sesión si la entrada ya está pagada.
        """
        if instance.estado == TicketStatus.PAGADA:
            seat_fields = {"sesion", "fila", "numero"}
            if seat_fields & set(validated_data.keys()):
                raise serializers.ValidationError(
                    {"non_field_errors": ["No se puede modificar el asiento de una entrada pagada."]}
                )
        return super().update(instance, validated_data)
