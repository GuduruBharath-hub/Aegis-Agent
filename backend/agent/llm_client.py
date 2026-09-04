from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.core.models import FailureEvidence, Finding


class PatchFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    new_content: str


class PatchProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str = Field(min_length=1)
    files: tuple[PatchFile, ...] = Field(min_length=1, max_length=3)

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
    ) -> PatchProposal:
        del finding, context, policy_summary
        index = len(self.calls)
        self.calls.append(failure_evidence)
        if index >= len(self._proposals):
            raise RuntimeError("stub patch sequence exhausted")
        return self._proposals[index]
