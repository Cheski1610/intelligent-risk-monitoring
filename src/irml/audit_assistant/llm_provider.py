"""Optional Ollama generation through HTTP or an existing Docker container."""
from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from irml.common.config import settings
from irml.audit_assistant.prompts import SYSTEM_INSTRUCTIONS

_CURSOR_ERASE = re.compile(r"\x1b\[(\d*)D\x1b\[K")
_ANSI_CSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _clean_terminal_output(text: str) -> str:
    """Remove Ollama CLI cursor edits and terminal control characters."""
    parts: list[str] = []
    cursor = 0
    for match in _CURSOR_ERASE.finditer(text):
        parts.append(text[cursor : match.start()])
        current = "".join(parts)
        line_start = current.rfind("\n") + 1
        chars_to_remove = min(
            int(match.group(1) or "1"), len(current) - line_start
        )
        if chars_to_remove:
            parts = [current[:-chars_to_remove]]
        cursor = match.end()
    parts.append(text[cursor:])

    clean = _ANSI_CSI.sub("", "".join(parts))
    output: list[str] = []
    for char in clean:
        if char in {"\b", "\x7f"}:
            if output and output[-1] != "\n":
                output.pop()
        elif char == "\r":
            while output and output[-1] != "\n":
                output.pop()
        elif char >= " " or char in {"\n", "\t"}:
            output.append(char)
    return "".join(output).strip()


class TextGenerator(Protocol):
    def generate(self, prompt: str) -> str: ...


@dataclass(frozen=True, slots=True)
class ProviderSettings:
    mode: str = settings.ollama_mode
    base_url: str = settings.ollama_base_url
    container: str = settings.ollama_docker_container
    model: str = settings.ollama_model
    timeout_seconds: int = settings.ollama_timeout_seconds


class OllamaProvider:
    def __init__(self, provider_settings: ProviderSettings | None = None) -> None:
        self.config = provider_settings or ProviderSettings()
        if self.config.mode not in {"http", "docker"}:
            raise ValueError("OllamaProvider mode must be 'http' or 'docker'.")
        if not self.config.model:
            raise ValueError("Se requiere el nombre exacto del modelo Ollama.")

    def generate(self, prompt: str) -> str:
        if self.config.mode == "docker":
            return self._generate_docker(prompt)
        return self._generate_http(prompt)

    def _generate_docker(self, prompt: str) -> str:
        command = [
            "docker", "exec", "-i", self.config.container,
            "ollama", "run", "--think=false", "--hidethinking", self.config.model,
        ]
        try:
            result = subprocess.run(
                command,
                input=f"{SYSTEM_INSTRUCTIONS}\n\n{prompt}",
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=self.config.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"No se pudo invocar Ollama en Docker: {exc}") from exc
        if result.returncode != 0:
            detail = result.stderr.strip()[-500:]
            raise RuntimeError(f"Ollama en Docker devolvió un error: {detail}")
        answer = _clean_terminal_output(result.stdout)
        if not answer:
            raise RuntimeError("Ollama en Docker no devolvió texto.")
        return answer

    def _generate_http(self, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.config.model,
                "system": SYSTEM_INSTRUCTIONS,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {"num_predict": 1200, "temperature": 0.2},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.config.timeout_seconds
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"No se pudo conectar con Ollama: {exc}") from exc
        if payload.get("error"):
            raise RuntimeError(f"Ollama devolvió un error: {payload['error']}")
        answer = str(payload.get("response", "")).strip()
        if not answer:
            raise RuntimeError("Ollama no devolvió texto.")
        return answer


def configured_provider() -> TextGenerator | None:
    if settings.ollama_mode == "disabled":
        return None
    if settings.ollama_mode not in {"http", "docker"}:
        raise ValueError("OLLAMA_MODE debe ser disabled, http o docker.")
    return OllamaProvider()
