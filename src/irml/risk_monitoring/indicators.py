"""Indicator labels and operational descriptions shown in the UI."""
from __future__ import annotations

INDICATORS = {
    "estimated_transaction_count": {
        "label": "Frecuencia estimada",
        "description": "Conteo aproximado usando el factor de expansión por step.",
        "direction": "both",
    },
    "estimated_amount_sum": {
        "label": "Importe total estimado",
        "description": "Suma de importes ponderada por el factor de expansión.",
        "direction": "both",
    },
    "mean_amount": {
        "label": "Importe promedio de la muestra",
        "description": "Promedio de importes de las filas seleccionadas en cada periodo.",
        "direction": "both",
    },
    "p95_amount": {
        "label": "Percentil 95 del importe",
        "description": "Percentil calculado sobre la muestra del periodo.",
        "direction": "both",
    },
    "active_origins": {
        "label": "Originadores distintos observados",
        "description": "Número de identificadores de origen distintos en la muestra.",
        "direction": "both",
    },
    "top_destination_share": {
        "label": "Concentración en el destino principal",
        "description": "Proporción de filas de la muestra dirigidas al destino más frecuente.",
        "direction": "high",
    },
    "alert_rate": {
        "label": "Tasa de alertas",
        "description": "Proporción de filas con alerta analítica adjunta, si se proporcionó.",
        "direction": "high",
    },
}
