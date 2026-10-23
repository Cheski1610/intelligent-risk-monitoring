from __future__ import annotations

from pathlib import Path

from irml.audit_assistant.documents import load_document_chunks
from irml.audit_assistant.investigation import SECTION_TITLES, create_investigation
from irml.audit_assistant.llm_provider import _clean_terminal_output
from irml.audit_assistant.retrieval import LexicalRetriever
from irml.common.schemas import Alert, AlertSeverity


class FailingProvider:
    def generate(self, prompt: str) -> str:
        raise RuntimeError("provider offline")


def sample_alert() -> Alert:
    return Alert(
        source_tool="anomaly_detection",
        event_step=24,
        transaction_id="28",
        risk_category="importe_inusual",
        score_type="anomaly_score",
        score_value=4.2,
        severity=AlertSeverity.MEDIUM,
        reason_codes=["amount_above_reference_threshold"],
        observed_values={"amount": 1000.0, "type": "TRANSFER"},
    )


def test_retrieval_preserves_document_references():
    root = Path(__file__).parents[1] / "data" / "synthetic_documents"
    chunks = load_document_chunks(root)
    results = LexicalRetriever(chunks).search("validar transacción autorización", limit=3)

    assert results
    assert all(":v" in item.chunk.reference and "#" in item.chunk.reference for item in results)


def test_unmatched_query_returns_no_evidence():
    root = Path(__file__).parents[1] / "data" / "synthetic_documents"
    retriever = LexicalRetriever(load_document_chunks(root))

    assert retriever.search("zzqv xxyy qwertyasdf", limit=5) == []


def test_deterministic_investigation_has_ten_sections_without_documents():
    draft = create_investigation(sample_alert(), [])

    assert draft.provider_mode == "deterministic"
    assert tuple(draft.sections) == SECTION_TITLES
    assert "No se recuperaron" in draft.sections["Referencias documentales"]


def test_provider_error_falls_back_to_deterministic_template():
    draft = create_investigation(sample_alert(), [], FailingProvider())

    assert draft.provider_mode == "deterministic_fallback"
    assert draft.provider_error == "provider offline"
    assert draft.generated_text is None


def test_ollama_cli_cursor_edits_are_removed_from_generated_text():
    raw = "Texto p\x1b[1D\x1b[Kproporcionado.\x1b[?25h"

    assert _clean_terminal_output(raw) == "Texto proporcionado."
