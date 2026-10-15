"""Imprime la revisión del día que toca ahora (vacío si ninguna). Solo usa la biblioteca estándar,
para decidirlo en segundos antes de instalar dependencias."""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dashboard import sesiones  # noqa: E402

now = dt.datetime.now(dt.timezone.utc)
hechos = {e["id"] for e in sesiones.cargar(sesiones.dia(now))}
print(sesiones.pendiente(now, hechos) or "")
