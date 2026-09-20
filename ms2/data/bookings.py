"""Booking data model and lookup."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class Booking:
    pnr: str
    flight_number: str
    origin: str
    destination: str
    scheduled_dt: datetime
    status: Literal["Cancelled", "Delayed", "Unaffected"]
    disruption_cause: Literal["airline", "passenger", "none"]
    delay_hours: float = 0.0
    new_departure_dt: datetime | None = None


_BOOKINGS: dict[str, list[Booking]] = {
    "SK4821X": [
        Booking(
            pnr="SK4821X",
            flight_number="SK-204",
            origin="Delhi",
            destination="Goa",
            scheduled_dt=datetime(2026, 9, 23, 18, 40),
            status="Cancelled",
            disruption_cause="airline",
        ),
        Booking(
            pnr="SK4821X",
            flight_number="SK-RETURN",
            origin="Goa",
            destination="Delhi",
            scheduled_dt=datetime(2026, 9, 25, 16, 20),
            status="Unaffected",
            disruption_cause="none",
        ),
    ],
    "TR1190B": [
        Booking(
            pnr="TR1190B",
            flight_number="SK-118",
            origin="Mumbai",
            destination="Bengaluru",
            scheduled_dt=datetime(2026, 9, 23, 7, 10),
            status="Delayed",
            disruption_cause="airline",
            delay_hours=4.0,
            new_departure_dt=datetime(2026, 9, 23, 11, 10),
        ),
    ],
    "WL7742": [
        Booking(
            pnr="WL7742",
            flight_number="SK-305",
            origin="Delhi",
            destination="Hyderabad",
            scheduled_dt=datetime(2026, 9, 23, 14, 0),
            status="Delayed",
            disruption_cause="airline",
            delay_hours=6.0,
            new_departure_dt=datetime(2026, 9, 23, 20, 0),
        ),
    ],
}


def get_bookings_by_pnr(pnr: str) -> list[Booking]:
    """Return all bookings for the given PNR. Empty list if not found."""
    return _BOOKINGS.get(pnr.upper(), [])


def get_affected_booking(pnr: str) -> Booking | None:
    """Return the first Cancelled or Delayed booking for the given PNR."""
    for booking in get_bookings_by_pnr(pnr):
        if booking.status in ("Cancelled", "Delayed"):
            return booking
    return None
