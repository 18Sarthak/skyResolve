import type { Customer } from "@/data/customers";

interface CaseHeaderProps {
  customer: Customer;
  escalated: boolean;
}

const time = (date: string) => date.slice(11, 16);

export function TierBadge({ tier }: { tier: Customer["tier"] }) {
  return <span className={`tier-badge tier-${tier.toLowerCase()}`}>{tier}</span>;
}

export function StatusChip({ customer }: { customer: Customer }) {
  const label = customer.status === "Delayed" ? `Delayed ${customer.delayHours}h` : customer.status;
  return (
    <span className={`status-chip status-${customer.status.toLowerCase().replace(" ", "-")}`}>
      {label}
    </span>
  );
}

export function CaseHeader({ customer, escalated }: CaseHeaderProps) {
  return (
    <header className="case-header">
      <div className="case-header-primary">
        <div className="case-person">
          <strong>{customer.name}</strong>
          <TierBadge tier={customer.tier} />
        </div>
        <span className="pnr-code">{customer.pnr}</span>
        <span className="case-flight">
          {customer.flightNumber} <span aria-hidden="true">·</span> {customer.route.from}{" "}
          <span aria-hidden="true">→</span> {customer.route.to}
        </span>
        <StatusChip customer={customer} />
        {customer.status === "Delayed" && customer.newDepartureDt ? (
          <span className="schedule-shift">
            Scheduled {time(customer.scheduledDt)} <span aria-hidden="true">→</span> Now{" "}
            {time(customer.newDepartureDt)} (+{customer.delayHours}h)
          </span>
        ) : null}
      </div>
      <span className={`case-state ${escalated ? "case-state-escalated" : "case-state-active"}`}>
        <span className="state-dot" />
        {escalated ? "Escalated" : "Active"}
      </span>
    </header>
  );
}
