"""Configuration loader and validator for Mumbai PM2.5 forecasting."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "default.yaml"


@dataclass
class PipelineConfig:
    """Strongly typed pipeline configuration."""
    paths: dict[str, str] = field(default_factory=dict)
    time: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    features: dict[str, Any] = field(default_factory=dict)
    models: dict[str, Any] = field(default_factory=dict)
    external_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | str | None = None) -> PipelineConfig:
        cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
        if not cfg_path.is_file():
            raise FileNotFoundError(f"Config file not found: {cfg_path}")
        with cfg_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(
            paths=data.get("paths", {}),
            time=data.get("time", {}),
            validation=data.get("validation", {}),
            features=data.get("features", {}),
            models=data.get("models", {}),
            external_data=data.get("external_data", {}),
        )


def get_config(path: Path | str | None = None) -> PipelineConfig:
    """Get active pipeline configuration."""
    return PipelineConfig.load(path)
