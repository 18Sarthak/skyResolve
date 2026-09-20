"""Customer data model and lookup."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Customer:
    pnr: str
    name: str
    tier: Literal["Silver", "Gold", "Platinum"]


_CUSTOMERS: dict[str, Customer] = {
    "SK4821X": Customer(pnr="SK4821X", name="Priya Nair", tier="Gold"),
    "TR1190B": Customer(pnr="TR1190B", name="Arvind Kulkarni", tier="Silver"),
    "WL7742": Customer(pnr="WL7742", name="Meher Kaur", tier="Platinum"),
}


def get_customer_by_pnr(pnr: str) -> Customer | None:
    """Return the Customer for the given PNR, or None if not found."""
    return _CUSTOMERS.get(pnr.upper())
