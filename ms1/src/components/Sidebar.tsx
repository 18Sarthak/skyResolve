import { History, Plane } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CUSTOMERS, DEFAULT_CUSTOMER, type Customer } from "@/data/customers";
import { StatusChip, TierBadge } from "./CaseHeader";

interface SidebarProps {
  selectedPnr: string;
  onSelect: (pnr: string) => void;
  onOpenHistory: () => void;
}

function CustomerCard({
  customer,
  active,
  onSelect,
}: {
  customer: Customer;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      className={`customer-card ${active ? "customer-card-active" : ""}`}
      onClick={onSelect}
      type="button"
    >
      <div className="customer-card-top">
        <strong>{customer.name}</strong>
        <TierBadge tier={customer.tier} />
      </div>
      <span className="pnr-code">{customer.pnr}</span>
      <div className="customer-card-bottom">
        <span>
          {customer.route.from} <span aria-hidden="true">→</span> {customer.route.to}
        </span>
        <StatusChip customer={customer} />
      </div>
    </button>
  );
}

export function Sidebar({ selectedPnr, onSelect, onOpenHistory }: SidebarProps) {
  const selected = CUSTOMERS.find((customer) => customer.pnr === selectedPnr) ?? DEFAULT_CUSTOMER;

  return (
    <aside className="sidebar">
      <div className="brand-block">
        <span className="brand-mark" aria-hidden="true">
          <Plane />
        </span>
        <div>
          <strong>SkyResolve</strong>
          <span>Operations console</span>
        </div>
      </div>

      <div className="sidebar-section customer-section">
        <span className="sidebar-label">Customer queue</span>
        <div className="customer-list">
          {CUSTOMERS.map((customer) => (
            <CustomerCard
              key={customer.pnr}
              customer={customer}
              active={customer.pnr === selectedPnr}
              onSelect={() => onSelect(customer.pnr)}
            />
          ))}
        </div>
      </div>

      <div className="sidebar-section active-case-summary">
        <span className="sidebar-label">Active case</span>
        <dl>
          <div>
            <dt>PNR</dt>
            <dd className="pnr-code">{selected.pnr}</dd>
          </div>
          <div>
            <dt>Flight</dt>
            <dd>{selected.flightNumber}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>
              <StatusChip customer={selected} />
            </dd>
          </div>
        </dl>
      </div>

      <div className="sidebar-footer">
        <Button className="history-button" onClick={onOpenHistory} variant="outline">
          <History /> View history
        </Button>
        <p>Policy-first. Human when it matters.</p>
      </div>
    </aside>
  );
}
