import { Clock3, Plane, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { HistoryTurn } from "@/api";
import type { Customer } from "@/data/customers";
import { ActionChips } from "./ActionsPanel";

interface HistoryDrawerProps {
  open: boolean;
  customer: Customer;
  turns: HistoryTurn[];
  loading: boolean;
  error: string | null;
  onClose: () => void;
}

const formatTimestamp = (timestamp: string) =>
  new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(timestamp));

export function HistoryDrawer({
  open,
  customer,
  turns,
  loading,
  error,
  onClose,
}: HistoryDrawerProps) {
  return (
    <>
      <button
        className={`drawer-backdrop ${open ? "drawer-backdrop-open" : ""}`}
        aria-label="Close history"
        onClick={onClose}
        type="button"
      />
      <aside
        className={`history-drawer ${open ? "history-drawer-open" : ""}`}
        aria-hidden={!open}
        aria-label="Conversation history"
      >
        <header className="drawer-header">
          <div>
            <span>Case history</span>
            <strong>
              {customer.name} · {customer.pnr}
            </strong>
          </div>
          <Button
            aria-label="Close history"
            className="drawer-close"
            onClick={onClose}
            size="icon"
            variant="ghost"
          >
            <X />
          </Button>
        </header>
        <div className="drawer-content">
          {loading ? (
            <div className="history-loading">
              <span />
              <span />
              <span />
            </div>
          ) : null}
          {error ? <p className="history-error">{error}</p> : null}
          {!loading && !error && !turns.length ? (
            <div className="history-empty">
              <Plane />
              <p>No previous turns for this case.</p>
            </div>
          ) : null}
          {!loading && !error
            ? turns.map((turn, index) => (
                <article className="history-turn" key={turn.id}>
                  <div className="history-turn-index">{String(index + 1).padStart(2, "0")}</div>
                  <div className="history-turn-body">
                    <time>
                      <Clock3 /> {formatTimestamp(turn.timestamp)}
                    </time>
                    <p>{turn.customer_message}</p>
                    <ActionChips actions={turn.actions_taken_json} />
                    {turn.escalated ? (
                      <span
                        className="history-escalated"
                        title={turn.escalation_reason ?? undefined}
                      >
                        Escalated
                      </span>
                    ) : null}
                    <span className="token-usage">
                      ↑ {turn.prompt_tokens} &nbsp; ↓ {turn.completion_tokens} tokens
                    </span>
                  </div>
                </article>
              ))
            : null}
        </div>
      </aside>
    </>
  );
}
