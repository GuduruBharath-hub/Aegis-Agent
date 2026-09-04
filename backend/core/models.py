from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Finding:
    id: str
    scanner: str
    rule_id: str
    category: str
    cwe: str
    severity: str
    confidence: str
    file_path: str
    line_start: int
    line_end: int
    symbol: str
    message: str
