"""Temporal risk indicator monitoring application."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from apps.shared import (
    load_cached_expansion_weights,
    load_selected_data,
    show_nav_links,
    show_quality,
)
from irml.common.alert_store import load_alerts, upsert_alerts
from irml.common.config import settings
from irml.common.exports import csv_bytes, records_to_frame
from irml.risk_monitoring.alerts import alerts_from_changes
from irml.risk_monitoring.aggregation import aggregate_indicators
from irml.risk_monitoring.change_detection import detect_changes
from irml.risk_monitoring.indicators import INDICATORS
from irml.risk_monitoring.replay import shift_replay_period

show_nav_links()
st.title("Monitor de indicadores y cambios")
st.caption(
    "step es una hora simulada. El replay sigue el orden histórico del archivo; "
    "no es una transmisión en tiempo real."
)

frame, quality, source_label, source_path = load_selected_data()
show_quality(quality)
weights = load_cached_expansion_weights(
    str(settings.project_root / "reports" / "paysim_profile_by_step.csv")
)
try:
    stored_alerts = load_alerts(settings.alert_store_path)
except Exception as exc:
    stored_alerts = []
    st.warning(f"No se pudieron leer las alertas compartidas: {exc}")
anomaly_ids = {
    alert.transaction_id
    for alert in stored_alerts
    if alert.source_tool == "anomaly_detection" and alert.transaction_id
}
frame = frame.copy()
frame["_anomaly_flag"] = frame["_source_row_id"].astype("string").isin(anomaly_ids)

with st.sidebar:
    granularity_label = st.selectbox("Granularidad", ["Por hora simulada", "Por día simulado"])
    indicator_label = st.selectbox(
        "Indicador",
        options=list(INDICATORS),
        format_func=lambda key: INDICATORS[key]["label"],
    )
    multiplier = st.slider("Límite robusto (multiplicador)", 2.0, 6.0, 3.5, 0.5)
    persistence = st.slider("Periodos consecutivos para alertar", 1, 5, 2)

granularity = "hour" if granularity_label.startswith("Por hora") else "day"
indicators = aggregate_indicators(
    frame,
    granularity=granularity,
    expansion_weights=weights,
)
if indicators.empty:
    st.warning("No hay filas suficientes para calcular indicadores.")
    st.stop()

try:
    changes, limit = detect_changes(
        indicators,
        indicator_label,
        last_reference_step=323,
        multiplier=float(multiplier),
        minimum_persistence=int(persistence),
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

st.caption(
    f"Fuente: {source_path.name} · {len(indicators):,} periodos · "
    f"{limit.reference_periods:,} periodos en la referencia."
)
st.markdown(f"**Definición:** {INDICATORS[indicator_label]['description']}")
c1, c2, c3 = st.columns(3)
c1.metric("Mediana de referencia", f"{limit.median:,.3f}")
c2.metric("Límite inferior", f"{limit.lower:,.3f}")
c3.metric("Límite superior", f"{limit.upper:,.3f}")

first_period = int(changes["period"].min())
last_period = int(changes["period"].max())
replay_period_key = f"irml_replay_period_{granularity}"
replay_running_key = f"irml_replay_running_{granularity}"
if replay_period_key not in st.session_state:
    st.session_state[replay_period_key] = first_period
else:
    st.session_state[replay_period_key] = max(
        first_period, min(last_period, int(st.session_state[replay_period_key]))
    )

with st.sidebar:
    replay_interval = st.selectbox(
        "Velocidad de reproducción",
        options=[0.25, 0.5, 1.0, 2.0],
        index=2,
        format_func=lambda seconds: {
            0.25: "4 periodos por segundo",
            0.5: "2 periodos por segundo",
            1.0: "1 periodo por segundo",
            2.0: "1 periodo cada 2 segundos",
        }[seconds],
    )


@st.fragment(run_every=float(replay_interval))
def show_replay(data: pd.DataFrame) -> None:
    if st.session_state.get(replay_running_key, False):
        next_period = shift_replay_period(
            int(st.session_state[replay_period_key]),
            1,
            first_period=first_period,
            last_period=last_period,
        )
        st.session_state[replay_period_key] = next_period
        if next_period == last_period:
            st.session_state[replay_running_key] = False

    st.subheader("Reproducción temporal")
    controls = st.columns(4)
    if controls[0].button("Reiniciar", key=f"replay_reset_{granularity}"):
        st.session_state[replay_period_key] = first_period
        st.session_state[replay_running_key] = False
    if controls[1].button("Anterior", key=f"replay_previous_{granularity}"):
        st.session_state[replay_period_key] = shift_replay_period(
            int(st.session_state[replay_period_key]),
            -1,
            first_period=first_period,
            last_period=last_period,
        )
    run_label = (
        "Pausar"
        if st.session_state.get(replay_running_key, False)
        else "Reproducir"
    )
    if controls[2].button(run_label, key=f"replay_toggle_{granularity}"):
        st.session_state[replay_running_key] = not st.session_state.get(
            replay_running_key, False
        )
    if controls[3].button("Siguiente", key=f"replay_next_{granularity}"):
        st.session_state[replay_period_key] = shift_replay_period(
            int(st.session_state[replay_period_key]),
            1,
            first_period=first_period,
            last_period=last_period,
        )

    current_period = st.slider(
        "Último periodo reproducido",
        min_value=first_period,
        max_value=last_period,
        key=replay_period_key,
    )
    visible = data.loc[data["period"].le(current_period)]
    fraction = (current_period - first_period) / max(last_period - first_period, 1)
    st.progress(fraction, text=f"Periodo {current_period} de {last_period}")
    current = visible.iloc[-1]
    if granularity == "hour":
        st.caption(f"step simulado {int(current['end_step'])}")
    else:
        st.caption(
            f"Día simulado {current_period} · hasta step {int(current['end_step'])}"
        )
    st.metric(
        INDICATORS[indicator_label]["label"],
        f"{float(current[indicator_label]):,.3f}",
    )

    replay_chart = go.Figure()
    replay_chart.add_trace(
        go.Scatter(
            x=visible["period"],
            y=visible[indicator_label],
            mode="lines+markers",
            name=INDICATORS[indicator_label]["label"],
        )
    )
    replay_chart.add_hline(
        y=limit.upper,
        line_dash="dash",
        line_color="#c0392b",
        annotation_text="Límite superior",
    )
    replay_chart.add_hline(
        y=limit.lower,
        line_dash="dash",
        line_color="#2874a6",
        annotation_text="Límite inferior",
    )
    reference_end = 323 if granularity == "hour" else (323 - 1) // 24 + 1
    replay_chart.add_vline(
        x=reference_end,
        line_dash="dot",
        annotation_text="Fin de referencia",
    )
    replay_chart.update_layout(
        xaxis_title="Periodo simulado",
        yaxis_title=INDICATORS[indicator_label]["label"],
        height=420,
        margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(replay_chart, width="stretch")


show_replay(changes)

st.subheader("Cambios que requieren revisión")
flagged = changes.loc[changes["is_alert"]]
alerts = alerts_from_changes(changes, indicator=indicator_label)
if flagged.empty:
    st.success("No se detectaron cambios persistentes que crucen los límites elegidos.")
else:
    st.dataframe(flagged, hide_index=True, width="stretch")
    alert_frame = records_to_frame(alerts)
    st.download_button(
        "Descargar alertas CSV",
        data=csv_bytes(alert_frame),
        file_name="alertas_monitor_riesgo.csv",
        mime="text/csv",
    )
    if st.button("Compartir alertas con el asistente"):
        saved = upsert_alerts(
            alerts, settings.alert_store_path, source_tool="risk_monitoring"
        )
        st.success(f"Alertas disponibles para el asistente en {saved}.")

with st.expander("Método y lectura"):
    st.markdown(
        "La referencia usa solo periodos que terminan hasta step 323. "
        "El límite se calcula con mediana y MAD; si MAD es cero se usa desviación "
        "estándar. Una alerta requiere cruce persistente según el control seleccionado. "
        "El conteo e importe total estimados usan los factores de expansión por step; "
        "percentiles y concentración describen la muestra."
    )

st.download_button(
    "Descargar indicadores CSV",
    data=csv_bytes(indicators),
    file_name="indicadores_riesgo.csv",
    mime="text/csv",
)
