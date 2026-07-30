"""Shared helper for building Evidence lists with stable sequential IDs."""

from ..models import Evidence, EvidenceCategory


class EvidenceBuilder:
    def __init__(self, case_id: str):
        self.case_id = case_id
        self.items: list[Evidence] = []

    def add(self, category: EvidenceCategory, label: str, value: str, source: str) -> None:
        self.items.append(
            Evidence(
                id=f"{self.case_id}-EV{len(self.items) + 1:03d}",
                case_id=self.case_id,
                category=category,
                label=label,
                value=value.strip(),
                source_location=source,
            )
        )
