"""The decision for one open order."""
from typing import Literal

from pydantic import BaseModel, Field


class Decision(BaseModel):
    po_number: str
    action: Literal["none", "chase_supplier", "escalate"]
    reason: str = Field(min_length=1)
