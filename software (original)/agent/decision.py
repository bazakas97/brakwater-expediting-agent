"""The decision for one open order."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_REASON_WORDS = 20


class Decision(BaseModel):
    po_number: str
    action: Literal["none", "chase_supplier", "escalate"]
    reason: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def reason_must_be_short(cls, reason: str) -> str:
        words = len(reason.split())
        if words > MAX_REASON_WORDS:
            raise ValueError(f"reason has {words} words, max is {MAX_REASON_WORDS}")
        return reason
