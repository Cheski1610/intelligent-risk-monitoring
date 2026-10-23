"""Small shared Streamlit helpers for all application pages."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from irml.common.config import settings
from irml.data.loader import load_transactions
from irml.risk_monitoring.aggregation import load_expansion_weights


@st.cache_data(show_spinner=False, max_entries=4)
def load_cached_transactions(path_text: str) -> tuple[Any, dict[str, Any]]:
    loaded = load_transactions(path_text)
    return loaded.frame, loaded.quality.to_dict()


@st.cache_data(show_spinner=False, max_entries=2)
def load_cached_expansion_weights(path_text: str) -> dict[int, float]:
    path = Path(path_text)
    return load_expansion_weights(str(path)) if path.is_file() else {}


def selected_data_path(label: str = "Fuente de transacciones"):
    sample_exists = settings.sample_path.is_file()
    options = ["Muestra reproducible", "CSV completo"]
    choice = st.sidebar.radio(label, options, index=0)
    if choice == options[0] and sample_exists:
        return choice, settings.sample_path
    if choice == options[0] and not sample_exists:
        st.sidebar.warning("No se encontró la muestra; se usará el CSV completo.")
    return "CSV completo", settings.data_path


def load_selected_data(label: str = "Fuente de transacciones"):
    choice, path = selected_data_path(label)
    if not path.is_file():
        st.error(
            f"No se encontró el archivo: {path}. Coloque PaySim en la raíz o "
            "genere la muestra con .venv\\Scripts\\python.exe scripts/profile_paysim.py."
        )
        st.stop()
    with st.spinner(f"Cargando {choice.lower()}..."):
        frame, quality = load_cached_transactions(str(path))
    return frame, quality, choice, path


def show_quality(quality: dict[str, Any]) -> None:
    if quality.get("has_quality_issues"):
        st.warning(
            "La carga encontró observaciones de calidad. Las filas se conservaron; "
            "revise el detalle antes de interpretar los resultados."
        )
        with st.expander("Detalle de calidad"):
            st.json(quality)
    else:
        st.caption(
            f"Calidad estructural: sin nulos, valores inválidos ni duplicados en "
            f"{quality.get('rows_processed', 0):,} filas."
        )


def show_nav_links() -> None:
    st.sidebar.caption("Use la navegación lateral de la aplicación principal para cambiar de herramienta.")
