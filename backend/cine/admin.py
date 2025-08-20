from __future__ import annotations

import csv
from datetime import timedelta
from typing import Iterable

from django.contrib import admin, messages
from django.db.models import Count, F, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html

from .models import Pelicula, Sesion, Entrada, TicketStatus


# =========================
# Filtros personalizados
# =========================
class DisponibilidadFilter(admin.SimpleListFilter):
    """
    Filtra sesiones por disponibilidad de asientos.
    """
    title = "disponibilidad"
    parameter_name = "disp"

    def lookups(self, request, model_admin):
        return (
            ("disponible", "Con asientos"),
            ("agotada", "Agotadas"),
        )

    def queryset(self, request, queryset):
        queryset = queryset.annotate(
            total_asientos=F("filas") * F("columnas"),
            ocupados=Count("entradas", distinct=True),
        )
        if self.value() == "agotada":
            return queryset.filter(ocupados__gte=F("total_asientos"))
        if self.value() == "disponible":
            return queryset.filter(ocupados__lt=F("total_asientos"))
        return queryset


class ProximidadSesionFilter(admin.SimpleListFilter):
    """
    Filtra sesiones por rango temporal útil en la operativa diaria.
    """
    title = "cuándo"
    parameter_name = "cuando"

    def lookups(self, request, model_admin):
        return (
            ("hoy", "Hoy"),
            ("maniana", "Mañana"),
            ("24h", "Próximas 24 h"),
            ("7d", "Próx. 7 días"),
            ("pasadas", "Ya han pasado"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "hoy":
            return queryset.filter(inicio__date=timezone.localdate())
        if self.value() == "maniana":
            return queryset.filter(inicio__date=timezone.localdate() + timedelta(days=1))
        if self.value() == "24h":
            return queryset.filter(inicio__gte=now, inicio__lt=now + timedelta(hours=24))
        if self.value() == "7d":
            return queryset.filter(inicio__gte=now, inicio__lt=now + timedelta(days=7))
        if self.value() == "pasadas":
            return queryset.filter(inicio__lt=now)
        return queryset


class TieneEmailFilter(admin.SimpleListFilter):
    """
    Filtra entradas por si tienen email asociado.
    """
    title = "email"
    parameter_name = "con_email"

    def lookups(self, request, model_admin):
        return (
            ("si", "Con email"),
            ("no", "Sin email"),
        )

    def queryset(self, request, queryset):
        if self.value() == "si":
            return queryset.filter(~Q(email=""), email__isnull=False)
        if self.value() == "no":
            return queryset.filter(Q(email="") | Q(email__isnull=True))
        return queryset


# =========================
# Película
# =========================
@admin.register(Pelicula)
class PeliculaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "duracion_min", "clasificacion", "poster_preview")
    list_filter = ("clasificacion",)
    search_fields = ("titulo",)
    ordering = ("titulo",)
    list_per_page = 50
    save_on_top = True

    fieldsets = (
        (None, {"fields": ("titulo", "clasificacion", "duracion_min")}),
        ("Detalles", {"fields": ("descripcion", "poster_url")}),
    )

    @admin.display(description="Póster")
    def poster_preview(self, obj: Pelicula):
        if not obj.poster_url:
            return "—"
        return format_html(
            '<a href="{0}" target="_blank" rel="noopener"><img src="{0}" alt="poster" style="height:40px"/></a>',
            obj.poster_url,
        )


# =========================
# Entradas (Inline para Sesión)
# =========================
class EntradaInline(admin.TabularInline):
    model = Entrada
    fields = ("fila", "numero", "estado", "email", "creada_en")
    readonly_fields = ("creada_en",)
    extra = 0
    show_change_link = True


# =========================
# Sesión
# =========================
@admin.register(Sesion)
class SesionAdmin(admin.ModelAdmin):
    list_display = (
        "pelicula",
        "inicio",
        "sala",
        "filas",
        "columnas",
        "asientos_disponibles_col",
        "reservadas_col",
        "pagadas_col",
    )
    list_filter = (DisponibilidadFilter, ProximidadSesionFilter, "sala", "pelicula")
    search_fields = ("pelicula__titulo",)
    date_hierarchy = "inicio"
    autocomplete_fields = ("pelicula",)
    list_select_related = ("pelicula",)
    readonly_fields = ("asientos_totales",)
    inlines = (EntradaInline,)
    ordering = ("-inicio",)
    actions = ("exportar_entradas_csv",)

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("pelicula")
        return qs.annotate(
            total_asientos=F("filas") * F("columnas"),
            entradas_count=Count("entradas", distinct=True),
            reservadas_count=Count("entradas", filter=Q(entradas__estado=TicketStatus.RESERVADA), distinct=True),
            pagadas_count=Count("entradas", filter=Q(entradas__estado=TicketStatus.PAGADA), distinct=True),
        )

    @admin.display(description="Disponibles", ordering="total_asientos")
    def asientos_disponibles_col(self, obj: Sesion) -> int:
        total = getattr(obj, "total_asientos", obj.filas * obj.columnas)
        ocupados = getattr(obj, "entradas_count", obj.entradas.count())
        return max(total - ocupados, 0)

    @admin.display(description="Reservadas", ordering="reservadas_count")
    def reservadas_col(self, obj: Sesion) -> int:
        return getattr(obj, "reservadas_count", obj.entradas.filter(estado=TicketStatus.RESERVADA).count())

    @admin.display(description="Pagadas", ordering="pagadas_count")
    def pagadas_col(self, obj: Sesion) -> int:
        return getattr(obj, "pagadas_count", obj.entradas.filter(estado=TicketStatus.PAGADA).count())

    # --- Acción CSV: exporta TODAS las entradas de las sesiones seleccionadas ---
    @admin.action(description="Exportar ENTRADAS de sesiones seleccionadas (CSV)")
    def exportar_entradas_csv(self, request, queryset):
        """
        Crea un CSV con las entradas de las sesiones marcadas.
        Columnas: película, inicio, sala, asiento, estado, email, creada_en.
        """
        sesiones = list(queryset)
        if not sesiones:
            self.message_user(request, "No hay sesiones seleccionadas.", level=messages.WARNING)
            return

        now_local = timezone.localtime()
        filename = f"entradas_sesiones_{now_local:%Y%m%d_%H%M}.csv"
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        # BOM para compatibilidad con Excel
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(["Pelicula", "Inicio", "Sala", "Asiento", "Estado", "Email", "Creada_en"])

        entradas = (
            Entrada.objects.filter(sesion__in=sesiones)
            .select_related("sesion", "sesion__pelicula")
            .order_by("sesion__inicio", "fila", "numero")
            .iterator()
        )
        for e in entradas:
            writer.writerow([
                e.sesion.pelicula.titulo,
                timezone.localtime(e.sesion.inicio).strftime("%Y-%m-%d %H:%M"),
                e.sesion.sala,
                e.etiqueta_asiento,
                e.estado,
                e.email or "",
                timezone.localtime(e.creada_en).strftime("%Y-%m-%d %H:%M"),
            ])
        return response


# =========================
# Entrada
# =========================
@admin.register(Entrada)
class EntradaAdmin(admin.ModelAdmin):
    list_display = ("sesion", "etiqueta_asiento_col", "estado", "email_link", "creada_en")
    list_filter = ("estado", TieneEmailFilter, "sesion__sala", "sesion__pelicula")
    search_fields = ("email", "sesion__pelicula__titulo", "sesion__sala")
    autocomplete_fields = ("sesion",)
    list_select_related = ("sesion", "sesion__pelicula")
    date_hierarchy = "creada_en"
    list_per_page = 50
    save_on_top = True
    actions = ("marcar_como_pagadas", "marcar_como_reservadas", "exportar_csv")
    readonly_fields = ("creada_en",)

    fieldsets = (
        (None, {"fields": ("sesion", "fila", "numero")}),
        ("Compra", {"fields": ("estado", "email", "creada_en")}),
    )

    @admin.display(description="Asiento", ordering="fila")
    def etiqueta_asiento_col(self, obj: Entrada) -> str:
        return obj.etiqueta_asiento

    @admin.display(description="Email")
    def email_link(self, obj: Entrada):
        if not obj.email:
            return "—"
        return format_html('<a href="mailto:{0}">{0}</a>', obj.email)

    @admin.action(description="Marcar como PAGADAS")
    def marcar_como_pagadas(self, request, queryset):
        updated = queryset.update(estado=TicketStatus.PAGADA)
        self.message_user(request, f"{updated} entradas marcadas como pagadas.", level=messages.SUCCESS)

    @admin.action(description="Marcar como RESERVADAS")
    def marcar_como_reservadas(self, request, queryset):
        updated = queryset.update(estado=TicketStatus.RESERVADA)
        self.message_user(request, f"{updated} entradas marcadas como reservadas.", level=messages.SUCCESS)

    # --- Acción CSV: exporta las entradas seleccionadas ---
    @admin.action(description="Exportar seleccionadas (CSV)")
    def exportar_csv(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, "No hay entradas seleccionadas.", level=messages.WARNING)
            return

        now_local = timezone.localtime()
        filename = f"entradas_{now_local:%Y%m%d_%H%M}.csv"
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write("\ufeff")  # BOM para Excel

        writer = csv.writer(response)
        writer.writerow(["Pelicula", "Inicio", "Sala", "Asiento", "Estado", "Email", "Creada_en"])

        qs: Iterable[Entrada] = queryset.select_related("sesion", "sesion__pelicula").order_by(
            "sesion__inicio", "fila", "numero"
        )
        for e in qs:
            writer.writerow([
                e.sesion.pelicula.titulo,
                timezone.localtime(e.sesion.inicio).strftime("%Y-%m-%d %H:%M"),
                e.sesion.sala,
                e.etiqueta_asiento,
                e.estado,
                e.email or "",
                timezone.localtime(e.creada_en).strftime("%Y-%m-%d %H:%M"),
            ])
        return response

    def get_readonly_fields(self, request, obj: Entrada | None = None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj and obj.estado == TicketStatus.PAGADA:
            ro += ["sesion", "fila", "numero"]
        return ro
