from __future__ import annotations

from typing import Literal, Protocol

from backend.core.models import Finding


AdapterName = Literal["sql_injection", "command_injection"]


class VulnerabilityAdapter(Protocol):
    name: AdapterName

    def can_handle(self, finding: Finding) -> bool: ...
