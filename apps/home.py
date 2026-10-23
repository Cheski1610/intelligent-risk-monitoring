"""Streamlit multipage entry point."""
import streamlit as st

st.set_page_config(
    page_title="Intelligent Risk Monitoring Lab",
    page_icon="📊",
    layout="wide",
)

pages = [
    st.Page("home_content.py", title="Inicio", icon="🏠", default=True),
    st.Page("01_anomaly_detection.py", title="Detector de anomalías", icon="🔎"),
    st.Page("02_risk_monitoring.py", title="Monitor de riesgo", icon="📈"),
    st.Page("03_ai_audit_assistant.py", title="Asistente de investigación", icon="🧾"),
]
st.navigation(pages).run()
