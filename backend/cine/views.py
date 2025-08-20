from __future__ import annotations

from datetime import timedelta

import django_filters
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, F
from django.utils import timezone

from rest_framework import viewsets, mixins, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Pelicula, Sesion, Entrada, TicketStatus
from .serializers import PeliculaSerializer, SesionSerializer, EntradaSerializer


# =========================
# Filtros
# =========================
class SesionFilter(django_filters.FilterSet):
    """
    Filtros para Sesión:
    - por película y sala
    - por rango de fecha/hora (inicio_after / inicio_before)
    """
    inicio_after = django_filters.IsoDateTimeFilter(field_name="inicio", lookup_expr="gte")
    inicio_before = django_filters.IsoDateTimeFilter(field_name="inicio", lookup_expr="lte")

    class Meta:
        model = Sesion
        fields = ("pelicula", "sala", "inicio_after", "inicio_before")


class EntradaFilter(django_filters.FilterSet):
    """
    Filtros para Entradas:
    - por sesión, estado
    - por email (icontains)
    - por fecha de creación (rango)
    """
    email = django_filters.CharFilter(field_name="email", lookup_expr="icontains")
    creada_after = django_filters.IsoDateTimeFilter(field_name="creada_en", lookup_expr="gte")
    creada_before = django_filters.IsoDateTimeFilter(field_name="creada_en", lookup_expr="lte")

    class Meta:
        model = Entrada
        fields = ("sesion", "estado", "email", "creada_after", "creada_before")


# =========================
# Películas
# =========================
class PeliculaViewSet(viewsets.ModelViewSet):
    """
    CRUD de películas.
    """
    queryset = Pelicula.objects.all()
    serializer_class = PeliculaSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("titulo",)
    ordering_fields = ("titulo", "duracion_min")
    ordering = ("titulo",)


# =========================
# Sesiones
# =========================
class SesionViewSet(viewsets.ModelViewSet):
    """
    CRUD de sesiones con métricas anotadas para rendimiento.

    Endpoints extra:
    - GET /sesiones/{id}/asientos?include=estado
      Devuelve el layout de asientos de la sesión.
      include=estado → devuelve 'estado' en lugar de booleano ocupado.
    """
    serializer_class = SesionSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = SesionFilter
    search_fields = ("pelicula__titulo", "sala")
    ordering_fields = ("inicio", "sala")
    ordering = ("-inicio",)

    def get_queryset(self):
        # Anotamos recuentos por estado para que el serializer los aproveche sin N+1
        return (
            Sesion.objects.select_related("pelicula")
            .annotate(
                reservadas_count=Count("entradas", filter=Q(entradas__estado=TicketStatus.RESERVADA), distinct=True),
                pagadas_count=Count("entradas", filter=Q(entradas__estado=TicketStatus.PAGADA), distinct=True),
            )
        )

    @action(detail=True, methods=["get"])
    def asientos(self, request, pk=None):
        """
        Devuelve el mapa de asientos de la sesión.
        Query param:
          - include=estado → 'estado' ∈ {'libre','reservada','pagada'}
          - si se omite → 'ocupado' ∈ {true,false}
        """
        sesion: Sesion = self.get_object()
        include = request.query_params.get("include")

        # Obtenemos ocupación en una query
        entradas_qs = Entrada.objects.filter(sesion=sesion).values_list("fila", "numero", "estado")
        if include == "estado":
            estado_map = {(fila, num): estado for (fila, num, estado) in entradas_qs}
        else:
            ocupados = {(fila, num) for (fila, num, _estado) in entradas_qs}

        layout = []
        for i in range(sesion.filas):
            fila_letra = chr(ord("A") + i)
            fila = []
            for col in range(1, sesion.columnas + 1):
                if include == "estado":
                    estado = estado_map.get((fila_letra, col), None)
                    fila.append({
                        "fila": fila_letra,
                        "numero": col,
                        "estado": estado or "libre",
                    })
                else:
                    fila.append({
                        "fila": fila_letra,
                        "numero": col,
                        "ocupado": (fila_letra, col) in ocupados,
                    })
            layout.append(fila)

        return Response({
            "sesion": sesion.id,
            "pelicula": sesion.pelicula_id,
            "filas": sesion.filas,
            "columnas": sesion.columnas,
            "layout": layout,
            "generado_en": timezone.now(),
        })


# =========================
# Entradas
# =========================
class EntradaViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Gestión de entradas (reservas/pagos).

    - POST /entradas/ crea una reserva.
      *Conflictos de asiento* → 409.
    - POST /entradas/{id}/pagar marca como pagada (idempotente).
    """
    serializer_class = EntradaSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = EntradaFilter
    search_fields = ("email", "sesion__pelicula__titulo", "sesion__sala")
    ordering_fields = ("creada_en", "estado")
    ordering = ("-creada_en",)

    def get_queryset(self):
        return Entrada.objects.select_related("sesion", "sesion__pelicula").all()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Crea una entrada de forma transaccional.
        Si hay colisión por constraint (mismo asiento), responde 409.
        """
        try:
            return super().create(request, *args, **kwargs)
        except serializers.ValidationError as e:
            # UniqueTogetherValidator → ValidationError con non_field_errors
            detail = e.detail
            if isinstance(detail, dict) and "non_field_errors" in detail:
                msgs = [str(m) for m in detail["non_field_errors"]]
                msg = msgs[0] if msgs else "Asiento ya reservado o pagado para esa sesión."
                return Response({"detail": msg}, status=status.HTTP_409_CONFLICT)
            raise
        except IntegrityError:
            return Response(
                {"detail": "Asiento ya reservado o pagado para esa sesión."},
                status=status.HTTP_409_CONFLICT,
            )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def pagar(self, request, pk=None):
        """
        Marca una entrada como PAGADA. Idempotente:
        - Si ya estaba pagada, devuelve 200 con el recurso.
        """
        entrada: Entrada = self.get_object()

        if entrada.estado == TicketStatus.PAGADA:
            serializer = self.get_serializer(entrada)
            return Response(serializer.data, status=status.HTTP_200_OK)

        entrada.estado = TicketStatus.PAGADA
        entrada.save(update_fields=["estado"])
        serializer = self.get_serializer(entrada)
        return Response(serializer.data, status=status.HTTP_200_OK)
