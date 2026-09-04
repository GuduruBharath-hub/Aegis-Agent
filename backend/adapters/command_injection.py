from __future__ import annotations

from typing import Literal

from backend.core.models import Finding


class CommandInjectionAdapter:
    name: Literal["command_injection"] = "command_injection"

    def can_handle(self, finding: Finding) -> bool:
        return finding.category == "COMMAND_INJECTION"
