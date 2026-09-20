export type CustomerTier = "Silver" | "Gold" | "Platinum";
export type FlightStatus = "Cancelled" | "Delayed" | "On Time";

export interface Customer {
  pnr: string;
  name: string;
  tier: CustomerTier;
  flightNumber: string;
  route: { from: string; to: string };
  scheduledDt: string;
  status: FlightStatus;
  delayHours: number;
  newDepartureDt?: string;
}

export const CUSTOMERS: Customer[] = [
  {
    pnr: "SK4821X",
    name: "Priya Nair",
    tier: "Gold",
    flightNumber: "SK-204",
    route: { from: "Delhi", to: "Goa" },
    scheduledDt: "2026-09-23T18:40",
    status: "Cancelled",
    delayHours: 0,
  },
  {
    pnr: "TR1190B",
    name: "Arvind Kulkarni",
    tier: "Silver",
    flightNumber: "SK-118",
    route: { from: "Mumbai", to: "Bengaluru" },
    scheduledDt: "2026-09-23T07:10",
    status: "Delayed",
    delayHours: 4,
    newDepartureDt: "2026-09-23T11:10",
  },
  {
    pnr: "WL7742",
    name: "Meher Kaur",
    tier: "Platinum",
    flightNumber: "SK-305",
    route: { from: "Delhi", to: "Hyderabad" },
    scheduledDt: "2026-09-23T14:00",
    status: "Delayed",
    delayHours: 6,
    newDepartureDt: "2026-09-23T20:00",
  },
];

export const DEFAULT_CUSTOMER: Customer = CUSTOMERS[0] ?? {
  pnr: "SK4821X",
  name: "Priya Nair",
  tier: "Gold",
  flightNumber: "SK-204",
  route: { from: "Delhi", to: "Goa" },
  scheduledDt: "2026-09-23T18:40",
  status: "Cancelled",
  delayHours: 0,
};

export const ACTION_LABELS: Record<string, string> = {
  free_rebooking_within_24h: "Free Rebooking (24h)",
  full_refund: "Full Refund",
  priority_rebooking: "Priority Rebooking",
  meal_voucher: "Meal Voucher (₹500)",
  lounge_access: "Lounge Access",
  hotel_for_delayed_hours_only: "Hotel (Delayed Hours)",
  collect_fare_difference: "Fare Difference Collected",
  process_refund: "Refund Processed",
};

export const formatActionLabel = (action: string) => {
  const normalized = action.replace(/^(denied_|deny_|rejected_)/, "");
  return (
    ACTION_LABELS[normalized] ??
    normalized.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
  );
};

export const isDeniedAction = (action: string) => /^(denied_|deny_|rejected_)/.test(action);
