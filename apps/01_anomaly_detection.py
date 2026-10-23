"""Interactive anomaly detection application."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from apps.shared import load_selected_data, show_nav_links, show_quality
from irml.anomaly_detection.evaluation import evaluate_scores
from irml.anomaly_detection.models import GaussianMixtureDetector
from irml.anomaly_detection.rules import RobustAmountRules
from irml.anomaly_detection.scoring import build_anomaly_alerts
from irml.common.alert_store import upsert_alerts
from irml.common.config import settings
from irml.common.exports import csv_bytes, records_to_frame

show_nav_links()
st.title("Detector de anomalías transaccionales")
st.caption(
    "GMM identifica baja verosimilitud estadística. Su puntaje no es una "
    "probabilidad de fraude."
)

frame, quality, source_label, source_path = load_selected_data()
show_quality(quality)
st.caption(f"Fuente: {source_path.name} · {len(frame):,} filas cargadas.")

with st.sidebar.form("detector_settings"):
    max_components = st.slider("Máximo de componentes GMM", 1, 5, 3)
    alert_quantile = st.slider(
        "Cuantil de referencia para alertas",
        min_value=0.980,
        max_value=0.999,
        value=0.995,
        step=0.001,
    )
    alert_limit = st.number_input("Máximo de alertas a mostrar", 50, 2000, 500, 50)
    run_detector = st.form_submit_button("Ajustar y puntuar", type="primary")

if run_detector:
    reference = frame.loc[pd.to_numeric(frame["step"], errors="coerce").le(323)]
    if len(reference) > 250_000:
        reference = reference.sample(n=250_000, random_state=settings.sample_seed)
        st.info(
            "Para limitar memoria, el ajuste GMM usa una submuestra reproducible "
            "de 250,000 filas del periodo de referencia."
        )
    try:
        with st.spinner("Ajustando GMM y reglas con el periodo de referencia..."):
            detector = GaussianMixtureDetector(
                max_components=int(max_components),
                seed=settings.sample_seed,
                alert_quantile=float(alert_quantile),
                max_iter=80,
            )
            fit_summary = detector.fit(reference)
            scores = detector.score(frame)
            gmm_flags = scores.ge(fit_summary.score_threshold).fillna(False)

            rules = RobustAmountRules(quantile=0.99, mad_multiplier=6.0)
            rules.fit(reference)
            rule_results = rules.explain(frame)
            all_flags = gmm_flags | rule_results["amount_rule_alert"]
            reasons = pd.Series(
                [
                    (
                        (["gmm_low_likelihood"] if gmm_flags.loc[index] else [])
                        + rule_results.loc[index, "reason_codes"]
                    )
                    for index in frame.index
                ],
                index=frame.index,
                dtype="object",
            )
            alerts = build_anomaly_alerts(
                frame,
                scores,
                all_flags,
                limit=int(alert_limit),
                reason_codes=reasons,
            )

            scored = frame.copy()
            scored["anomaly_score"] = scores
            scored["gmm_alert"] = gmm_flags
            scored["amount_rule_alert"] = rule_results["amount_rule_alert"]
            scored["reason_codes"] = reasons
            test_mask = pd.to_numeric(frame["step"], errors="coerce").between(379, 743)
            retrospective = evaluate_scores(
                frame.loc[test_mask, "isFraud"],
                scores.loc[test_mask],
                threshold=fit_summary.score_threshold,
            )
            rule_retrospective = evaluate_scores(
                frame.loc[test_mask, "isFraud"],
                rule_results.loc[test_mask, "amount_rule_alert"].fillna(False).astype(float),
                threshold=0.5,
            )
        st.session_state["irml_anomaly_scored"] = scored
        st.session_state["irml_anomaly_alerts"] = alerts
        st.session_state["irml_anomaly_fit"] = fit_summary
        st.session_state["irml_anomaly_eval"] = retrospective
        st.session_state["irml_anomaly_rule_eval"] = rule_retrospective
    except Exception as exc:
        st.error(f"No se pudo ejecutar el detector: {exc}")

scored = st.session_state.get("irml_anomaly_scored")
alerts = st.session_state.get("irml_anomaly_alerts", [])
fit_summary = st.session_state.get("irml_anomaly_fit")
if scored is not None and fit_summary is not None:
    st.subheader("Resultados")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Componentes GMM", fit_summary.selected_components)
    c2.metric("Umbral de anomalía", f"{fit_summary.score_threshold:.4f}")
    c3.metric("Señales priorizadas", f"{len(alerts):,}")
    c4.metric("Filas inválidas para GMM", f"{fit_summary.invalid_reference_rows:,}")
    with st.expander("BIC por número de componentes"):
        st.dataframe(
            pd.DataFrame(
                [
                    {"Componentes": components, "BIC": value}
                    for components, value in fit_summary.bic_by_components.items()
                ]
            ),
            hide_index=True,
            width="stretch",
        )

    st.subheader("Evaluación retrospectiva")
    st.caption(
        "Solo se evalúan steps 379–743. Los umbrales y transformaciones se ajustaron "
        "antes de ese periodo."
    )
    gmm_eval = st.session_state.get("irml_anomaly_eval", {})
    rule_eval = st.session_state.get("irml_anomaly_rule_eval", {})
    comparison = []
    for label, result in (("GMM", gmm_eval), ("Regla robusta", rule_eval)):
        comparison.append(
            {
                "Método": label,
                "Filas": result.get("evaluated_rows", 0),
                "Alertas": result.get("alert_count", 0),
                "Precisión": result.get("precision"),
                "Recall": result.get("recall"),
                "F1": result.get("f1"),
                "PR-AUC": result.get("pr_auc"),
                "ROC-AUC": result.get("roc_auc"),
                "Precision@K": result.get("precision_at_k"),
                "Recall@K": result.get("recall_at_k"),
            }
        )
    st.dataframe(pd.DataFrame(comparison), hide_index=True, width="stretch")
    st.caption(
        "La regla robusta usa una señal binaria; PR-AUC y orden @K de esa regla "
        "pueden tener menor granularidad que los del puntaje GMM."
    )

    st.subheader("Alertas")
    if alerts:
        alert_frame = records_to_frame(alerts)
        st.dataframe(alert_frame, hide_index=True, width="stretch")
        st.download_button(
            "Descargar alertas CSV",
            data=csv_bytes(alert_frame),
            file_name="alertas_anomalias.csv",
            mime="text/csv",
        )
        if st.button("Compartir alertas con el asistente"):
            saved = upsert_alerts(
                alerts, settings.alert_store_path, source_tool="anomaly_detection"
            )
            st.success(f"Alertas disponibles para el asistente en {saved}.")

    flagged_indices = list(scored.index[scored["gmm_alert"] | scored["amount_rule_alert"]])[:500]
    if flagged_indices:
        selected_index = st.selectbox(
            "Inspeccionar una fila señalada",
            options=flagged_indices,
            format_func=lambda index: (
                f"Fila {scored.at[index, '_source_row_id']} · step "
                f"{scored.at[index, 'step']} · {scored.at[index, 'type']} · "
                f"importe {scored.at[index, 'amount']:,.2f}"
            ),
        )
        row = scored.loc[selected_index]
        st.json(
            {
                "ID local de fila": str(row["_source_row_id"]),
                "step": int(row["step"]),
                "type": str(row["type"]),
                "amount": float(row["amount"]),
                "puntaje GMM": float(row["anomaly_score"]),
                "códigos de motivo": row["reason_codes"],
                "nota": "Señal estadística; no confirma fraude.",
            }
        )
    else:
        st.info("No hay filas señaladas con los umbrales actuales.")
