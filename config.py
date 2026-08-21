from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    pass


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"Environment variable '{name}' must be an integer, got {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"Environment variable '{name}' must be a number, got {raw!r}") from exc


@dataclass(frozen=True)
class OcrSettings:
    langs: str = "rus+eng"
    dpi: int = 300
    conf_threshold: float = 0.80
    tesseract_cmd: str | None = None

    @classmethod
    def from_environment(cls, prefix: str = "OCR_") -> "OcrSettings":
        return cls(
            langs=_env_str(f"{prefix}LANGS", "rus+eng"),
            dpi=_env_int(f"{prefix}DPI", 300),
            conf_threshold=_env_float(f"{prefix}CONF_THRESHOLD", 0.80),
            tesseract_cmd=os.environ.get(f"{prefix}TESSERACT_CMD") or None,
        )
