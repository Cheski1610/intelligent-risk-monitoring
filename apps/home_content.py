"""Project overview and data readiness."""
from __future__ import annotations

import json

import streamlit as st

from apps.shared import show_nav_links
from irml.common.config import settings

show_nav_links()
st.title("Intelligent Risk Monitoring Lab")
st.write(
    "Laboratorio educativo para transformar transacciones en señales de riesgo, "
    "observar cambios temporales y reunir evidencia para la revisión del auditor."
)
st.info(
    "PaySim es sintético. Una anomalía o alerta orienta una investigación; "
    "no confirma fraude ni sustituye el juicio humano."
)

sample_exists = settings.sample_path.is_file()
source_exists = settings.data_path.is_file()
profile_path = settings.project_root / "reports" / "paysim_profile.json"
profile = {}
if profile_path.is_file():
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        profile = {}

first, second, third = st.columns(3)
first.metric("Fuente PaySim", "Disponible" if source_exists else "No encontrada")
second.metric("Muestra de demo", "Disponible" if sample_exists else "No encontrada")
third.metric("Filas perfiladas", f"{profile.get('rows', 0):,}" if profile else "Pendiente")

if sample_exists:
    st.success(f"Muestra lista: {settings.sample_path.name}")
else:
    st.warning(
        "Genere la muestra con .venv\\Scripts\\python.exe scripts/profile_paysim.py desde la raíz."
    )

if profile:
    st.subheader("Resumen de calidad")
    a, b, c, d = st.columns(4)
    a.metric("Steps disponibles", f"{profile.get('step_count', 0):,}")
    b.metric("Nulos", f"{sum(profile.get('missing_cells', {}).values()):,}")
    c.metric("Duplicados exactos", f"{profile.get('exact_duplicate_rows', 0):,}")
    fraud_count = int(profile.get("fraud_labels", {}).get("1", 0))
    row_count = int(profile.get("rows", 0))
    d.metric("Etiqueta sintética", f"{fraud_count / row_count:.3%}" if row_count else "—")
    st.caption(
        "El archivo local contiene steps 1–743. step es tiempo simulado, "
        "no una fecha calendario."
    )

st.subheader("Herramientas")
cards = st.columns(3)
cards[0].markdown("**Detector de anomalías**  \nReglas robustas y GMM con explicaciones.")
cards[1].markdown("**Monitor de riesgo**  \nIndicadores por periodo y cambios persistentes.")
cards[2].markdown("**Asistente de investigación**  \nRecuperación documental y expediente preliminar.")

with st.expander("Limitaciones principales"):
    st.markdown(
        "- El conjunto y sus etiquetas son sintéticos.\n"
        "- Los puntajes de anomalía no son probabilidades de fraude.\n"
        "- Las alertas requieren revisión humana y evidencia autorizada.\n"
        "- Los documentos del asistente son ficticios y educativos."
    )
