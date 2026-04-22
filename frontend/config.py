from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrontendConfig:
    app_version: str = "0.1.0"
    sidebar_width: int = 260
    content_max_width: int = 1100


CONFIG = FrontendConfig()

