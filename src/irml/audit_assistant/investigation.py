"""Structured evidence-grounded investigation drafts and fallback template."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from irml.audit_assistant.llm_provider import TextGenerator
from irml.audit_assistant.prompts import investigation_prompt
from irml.audit_assistant.retrieval import RetrievedChunk
from irml.common.schemas import Alert

SECTION_TITLES = (
    "Resumen de la alerta",
    "Datos observados",
    "Motivo de generación de la alerta",
    "Criterios documentales relacionados",
    "Hipótesis de investigación",
    "Procedimientos recomendados",
    "Evidencia adicional requerida",
    "Limitaciones y explicaciones alternativas",
    "Referencias documentales",
    "Validación humana",
)


@dataclass(slots=True)
class InvestigationDraft:
    alert_id: str
    sections: dict[str, str]
    generated_text: str | None
    provider_mode: str
    provider_error: str | None
    sources: list[RetrievedChunk]
    unsupported_references: list[str]


def deterministic_sections(
    alert: Alert,
    sources: list[RetrievedChunk],
) -> dict[str, str]:
    source_refs = [item.chunk.reference for item in sources]
    observations = ", ".join(
        f"{key}: {value}" for key, value in alert.observed_values.items()
    ) or "La alerta no incluye valores observados."
    references = "\n".join(
        f"- [{item.chunk.reference}] {item.chunk.title}, sección {item.chunk.section}: "
        f"{item.chunk.text[:240].strip()}"
        for item in sources
    ) or "No se recuperaron fragmentos documentales pertinentes."
    evidence_refs = "\n".join(f"- {reference}" for reference in alert.evidence_refs)
    reason_text = ", ".join(alert.reason_codes) or "No se registraron códigos de motivo."
    return {
        SECTION_TITLES[0]: (
            f"Alerta {alert.alert_id}, categoría {alert.risk_category}, "
            f"severidad {alert.severity}. Esta señal requiere revisión; no es un hallazgo."
        ),
        SECTION_TITLES[1]: observations,
        SECTION_TITLES[2]: (
            f"Tipo de puntaje: {alert.score_type}; valor: {alert.score_value}. "
            f"Códigos registrados: {reason_text}."
        ),
        SECTION_TITLES[3]: (
            "\n".join(f"- [{reference}]" for reference in source_refs)
            if source_refs
            else "No hay evidencia documental recuperada para asociar."
        ),
        SECTION_TITLES[4]: (
            "Como hipótesis de trabajo, validar si el patrón observado tiene una "
            "explicación operativa legítima y si coincide con los criterios citados. "
            "La alerta por sí sola no permite elegir entre explicaciones."
        ),
        SECTION_TITLES[5]: (
            "Confirmar la transacción en la fuente autorizada, contrastar el criterio "
            "documental citado y documentar el resultado de la revisión."
            if sources
            else "Consultar un procedimiento aprobado y documentar el resultado; "
            "no se recuperó un criterio documental específico."
        ),
        SECTION_TITLES[6]: (
            "Verificar registro original, hora de autorización, datos de contraparte "
            "permitidos y evidencia de revisión/control aplicable."
            + (f"\nReferencias de evidencia ya adjuntas:\n{evidence_refs}" if evidence_refs else "")
        ),
        SECTION_TITLES[7]: (
            "PaySim es sintético. Los datos de la alerta no incluyen contexto operativo "
            "externo; cambios legítimos, convenciones de simulación o calidad de datos "
            "pueden explicar la señal."
        ),
        SECTION_TITLES[8]: references,
        SECTION_TITLES[9]: (
            "Un auditor debe validar los datos, las fuentes y el contexto antes de "
            "documentar una conclusión. No se confirma fraude ni se recomienda una "
            "acción disciplinaria."
        ),
    }


def _citations_in(text: str) -> set[str]:
    import re
    return set(re.findall(r"\[([A-Z0-9_-]+:v[0-9.]+#[a-zA-Z0-9_-]+)\]", text))


def create_investigation(
    alert: Alert,
    sources: list[RetrievedChunk],
    provider: TextGenerator | None = None,
) -> InvestigationDraft:
    sections = deterministic_sections(alert, sources)
    if provider is None:
        return InvestigationDraft(
            alert_id=alert.alert_id,
            sections=sections,
            generated_text=None,
            provider_mode="deterministic",
            provider_error=None,
            sources=sources,
            unsupported_references=[],
        )
    try:
        generated = provider.generate(investigation_prompt(alert, sources))
    except Exception as exc:
        return InvestigationDraft(
            alert_id=alert.alert_id,
            sections=sections,
            generated_text=None,
            provider_mode="deterministic_fallback",
            provider_error=str(exc),
            sources=sources,
            unsupported_references=[],
        )
    allowed = {item.chunk.reference for item in sources}
    unsupported = sorted(_citations_in(generated) - allowed)
    return InvestigationDraft(
        alert_id=alert.alert_id,
        sections=sections,
        generated_text=generated,
        provider_mode="ollama",
        provider_error=None,
        sources=sources,
        unsupported_references=unsupported,
    )
