from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.core.models import FailureEvidence, Finding


class PatchModelError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ModelTechnicalError:
    component: str
    code: str
    message: str
    request_number: int
    max_requests: int


TechnicalErrorReporter = Callable[[ModelTechnicalError], Awaitable[None]]


class PatchFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    new_content: str


class LineRationale(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    changed_lines: tuple[int, ...] = Field(min_length=1)
    change_kind: Literal[
        "parameterize",
        "escape",
        "allowlist",
        "argv",
        "guard",
        "reorder",
        "other",
    ]
    why: str = Field(min_length=1)
    earns: str = Field(min_length=1)

    @model_validator(mode="after")
    def lines_are_positive_and_unique(self) -> LineRationale:
        if any(line < 1 for line in self.changed_lines):
            raise ValueError("changed line numbers must be positive")
        if len(self.changed_lines) != len(set(self.changed_lines)):
            raise ValueError("changed line numbers must be unique")
        return self


class BehaviourPreservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    behaviour: str = Field(min_length=1)
    preserved_by: str = Field(min_length=1)
    proven_by: str = Field(min_length=1)


class RejectedAlternative(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    approach: str = Field(min_length=1)
    why_not: str = Field(min_length=1)


class PatchRationale(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    vulnerability_mechanism: str = Field(min_length=1)
    fix_mechanism: str = Field(min_length=1)
    line_rationales: tuple[LineRationale, ...]
    behaviour_preservation: tuple[BehaviourPreservation, ...]
    rejected_alternatives: tuple[RejectedAlternative, ...]
    residual_risk: tuple[str, ...]
    reviewer_must_confirm: tuple[str, ...]


class PatchProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str = Field(min_length=1)
    strategy: Literal[
        "parameterized_query",
        "argument_vector",
        "input_allowlist",
        "path_confinement",
        "other",
    ]
    files: tuple[PatchFile, ...] = Field(min_length=1, max_length=3)
    injection_observed: bool
    rationale: PatchRationale

    @model_validator(mode="after")
    def paths_are_unique(self) -> PatchProposal:
        paths = [file.path for file in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("patch paths must be unique")
        return self


class PatchModel(Protocol):
    name: str

    async def generate_patch(
        self,
        finding: Finding,
        context: str = "",
        policy_summary: str = "",
        failure_evidence: FailureEvidence | None = None,
        report_technical_error: TechnicalErrorReporter | None = None,
    ) -> PatchProposal: ...


class StubPatchModel:
    name = "stub"

    def __init__(self, proposals: tuple[PatchProposal, ...]) -> None:
        self._proposals = proposals
        self.calls: list[FailureEvidence | None] = []

    async def generate_patch(
        self,
        finding: Finding,
        context: str = "",
        policy_summary: str = "",
        failure_evidence: FailureEvidence | None = None,
        report_technical_error: TechnicalErrorReporter | None = None,
    ) -> PatchProposal:
        del finding, context, policy_summary, report_technical_error
        index = len(self.calls)
        self.calls.append(failure_evidence)
        if index >= len(self._proposals):
            raise RuntimeError("stub patch sequence exhausted")
        return self._proposals[index]
