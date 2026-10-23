"""Evidence retrieval and investigation-draft application."""
from __future__ import annotations

import json

import streamlit as st

from apps.shared import show_nav_links
from irml.audit_assistant.documents import load_document_chunks
from irml.audit_assistant.investigation import SECTION_TITLES, create_investigation
from irml.audit_assistant.llm_provider import OllamaProvider, ProviderSettings
from irml.audit_assistant.retrieval import LexicalRetriever
from irml.common.alert_store import load_alerts
from irml.common.config import settings
from irml.common.schemas import Alert

show_nav_links()
st.title("Asistente de investigación de alertas")
st.caption(
    "Recupera documentos educativos ficticios y prepara un borrador. "
    "Toda afirmación requiere validación humana."
)

try:
    alerts = load_alerts(settings.alert_store_path)
except Exception as exc:
    alerts = []
    st.error(f"No se pudieron leer las alertas compartidas: {exc}")

uploaded = st.file_uploader("O cargue una exportación JSON de alertas", type=["json"])
if uploaded is not None:
    try:
        raw_alerts = json.loads(uploaded.getvalue().decode("utf-8"))
        if not isinstance(raw_alerts, list):
            raise ValueError("El JSON debe contener una lista.")
        alerts = [Alert.model_validate(item) for item in raw_alerts]
    except Exception as exc:
        st.error(f"El archivo no contiene alertas válidas: {exc}")

if not alerts:
    st.info(
        "No hay alertas cargadas. Ejecute el detector o el monitor y seleccione "
        "Compartir alertas con el asistente, o cargue un JSON exportado."
    )
    st.stop()

alert_by_id = {alert.alert_id: alert for alert in alerts}
selected_alert_id = st.selectbox(
    "Alerta",
    list(alert_by_id),
    format_func=lambda alert_id: (
        f"{alert_id[:8]} · {alert_by_id[alert_id].source_tool} · "
        f"{alert_by_id[alert_id].risk_category} · step "
        f"{alert_by_id[alert_id].event_step or '—'}"
    ),
)
selected_alert = alert_by_id[selected_alert_id]
with st.expander("Datos recibidos"):
    st.json(selected_alert.model_dump(mode="json"))

documents_path = settings.project_root / "data" / "synthetic_documents"
chunks = load_document_chunks(documents_path)
retriever = LexicalRetriever(chunks)
default_query = " ".join([selected_alert.risk_category, *selected_alert.reason_codes])
query = st.text_input("Consulta documental", value=default_query)
retrieved = retriever.search(query, limit=5)

st.subheader("Fragmentos recuperados")
if retrieved:
    for item in retrieved:
        with st.expander(
            f"[{item.chunk.reference}] {item.chunk.title} · relevancia {item.score:.3f}"
        ):
            st.write(f"Sección: {item.chunk.section}")
            st.write(item.chunk.text)
else:
    st.warning("No se encontró evidencia documental con coincidencia léxica.")

provider_choice = st.radio(
    "Generación del expediente",
    ["Plantilla determinista", "Ollama en Docker"],
    horizontal=True,
)
if provider_choice == "Ollama en Docker":
    st.caption(
        f"Modelo: {settings.ollama_model} · API: {settings.ollama_base_url}. "
        "La generación solo se ejecuta "
        "al presionar el botón; si falla, se conserva la plantilla."
    )
    ollama_mode = st.selectbox(
        "Conexión Ollama",
        ["HTTP (contenedor Docker)", "Docker CLI"],
        index=1 if settings.ollama_mode == "docker" else 0,
    )
else:
    ollama_mode = "HTTP (contenedor Docker)"

if st.button("Generar expediente preliminar", type="primary"):
    provider = None
    if provider_choice == "Ollama en Docker":
        if ollama_mode == "Docker CLI":
            provider = OllamaProvider(
                ProviderSettings(
                    mode="docker",
                    container=settings.ollama_docker_container,
                    model=settings.ollama_model,
                    timeout_seconds=settings.ollama_timeout_seconds,
                )
            )
        else:
            provider = OllamaProvider(
                ProviderSettings(
                    mode="http",
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_model,
                    timeout_seconds=settings.ollama_timeout_seconds,
                )
            )
    with st.spinner("Preparando el expediente..."):
        draft = create_investigation(selected_alert, retrieved, provider)
    st.session_state["irml_investigation_draft"] = draft

draft = st.session_state.get("irml_investigation_draft")
if draft is not None and draft.alert_id == selected_alert.alert_id:
    if draft.provider_error:
        st.warning(
            "Ollama no estuvo disponible; se muestra la plantilla determinista. "
            f"Detalle: {draft.provider_error}"
        )
    elif draft.provider_mode == "ollama":
        st.success("Borrador generado con Ollama en Docker.")
    else:
        st.info("Borrador determinista; no se llamó a un modelo.")

    if draft.unsupported_references:
        st.warning(
            "La respuesta contiene referencias no presentes entre las fuentes "
            f"recuperadas: {draft.unsupported_references}"
        )
    if draft.generated_text:
        st.subheader("Borrador generado")
        st.markdown(draft.generated_text)
    else:
        st.subheader("Expediente determinista")
        for title in SECTION_TITLES:
            with st.expander(title, expanded=title == SECTION_TITLES[0]):
                st.markdown(draft.sections[title])

    markdown = ["# Expediente preliminar", f"Alerta: {draft.alert_id}", ""]
    if draft.generated_text:
        markdown.append(draft.generated_text)
    else:
        for title in SECTION_TITLES:
            markdown.extend([f"## {title}", draft.sections[title], ""])
    st.download_button(
        "Descargar expediente Markdown",
        data="\n".join(markdown).encode("utf-8"),
        file_name=f"expediente_{draft.alert_id[:8]}.md",
        mime="text/markdown",
    )
