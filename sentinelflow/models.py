"""Core Pydantic data models: Case, Evidence, Hypothesis, Critique."""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class EvidenceCategory(str, Enum):
    HEADER = "header"
    AUTHENTICATION = "authentication"
    ROUTING = "routing"
    URL = "url"
    ATTACHMENT = "attachment"
    BODY = "body"
    NETWORK = "network"  # used from Stage 2 onward


class Evidence(BaseModel):
    """One extracted fact. Produced only by deterministic parsers."""

    id: str  # e.g. "Q2_1-EV007", stable across reruns
    case_id: str
    category: EvidenceCategory
    label: str  # what the fact is, e.g. "SPF result"
    value: str  # the fact itself, verbatim from the source
    source_location: str  # where in the raw file it came from


class CaseStatus(str, Enum):
    PARSED = "parsed"
    INVESTIGATING = "investigating"
    APPROVED = "approved"
    UNRESOLVED = "unresolved_human_review_required"
    REPORTED = "reported"


class Case(BaseModel):
    case_id: str
    source_files: list[str]
    status: CaseStatus = CaseStatus.PARSED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Classification(str, Enum):
    PHISHING = "phishing"
    MALWARE_DELIVERY = "malware_delivery"
    SPAM = "spam"
    BENIGN = "benign"
    SUSPICIOUS_INCONCLUSIVE = "suspicious_inconclusive"


class ConfidenceLevel(str, Enum):
    """Routing signal only (low -> mandatory human review). Deliberately not
    a calibrated probability; see docs/evaluation_rubric.md."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Claim(BaseModel):
    """A single assertion the Investigator makes, individually checkable."""

    statement: str
    evidence_ids: list[str] = Field(min_length=1)


class AttackTechnique(BaseModel):
    technique_id: str  # e.g. "T1566.002"
    name: str
    evidence_ids: list[str] = Field(default_factory=list)


class Hypothesis(BaseModel):
    classification: Classification
    confidence: ConfidenceLevel
    summary: str
    claims: list[Claim]
    contradictory_evidence_ids: list[str] = Field(default_factory=list)
    attack_techniques: list[AttackTechnique] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class CritiqueVerdict(str, Enum):
    APPROVE = "approve"
    REVISE = "revise"


class UnsupportedClaim(BaseModel):
    claim_index: int  # index into Hypothesis.claims
    reason: str


class Critique(BaseModel):
    verdict: CritiqueVerdict
    unsupported_claims: list[UnsupportedClaim] = Field(default_factory=list)
    missing_considerations: list[str] = Field(default_factory=list)
    revised_confidence: ConfidenceLevel
    rationale: str


class PrecheckResult(BaseModel):
    """Mechanical (non-LLM) validation of citations before the Critic runs."""

    fabricated_evidence_ids: list[str] = Field(default_factory=list)
    claims_with_fabricated_ids: list[int] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.fabricated_evidence_ids
