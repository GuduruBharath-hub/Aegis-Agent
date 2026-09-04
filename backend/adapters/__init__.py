from __future__ import annotations

from backend.adapters.base import AdapterName, VulnerabilityAdapter
from backend.adapters.command_injection import CommandInjectionAdapter
from backend.adapters.sql_injection import SqlInjectionAdapter
from backend.core.models import Finding


_ADAPTERS: tuple[VulnerabilityAdapter, ...] = (
    SqlInjectionAdapter(),
    CommandInjectionAdapter(),
)


def select_adapter(finding: Finding) -> AdapterName:
    for adapter in _ADAPTERS:
        if adapter.can_handle(finding):
            return adapter.name
    raise ValueError(f"unsupported finding category: {finding.category}")
