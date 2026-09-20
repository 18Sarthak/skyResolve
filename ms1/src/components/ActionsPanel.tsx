import { Check, ChevronDown, CircleX, TriangleAlert } from "lucide-react";
import { formatActionLabel, isDeniedAction } from "@/data/customers";

interface ActionsPanelProps {
  actions: string[];
  escalated?: boolean | undefined;
  escalationReason?: string | null | undefined;
}

export function ActionChips({ actions }: { actions: string[] }) {
  return (
    <div className="action-chips">
      {actions.map((action) => {
        const denied = isDeniedAction(action);
        return (
          <span
            className={`action-chip ${denied ? "action-denied" : "action-approved"}`}
            key={action}
          >
            {denied ? <CircleX /> : <Check />}
            {formatActionLabel(action)}
          </span>
        );
      })}
    </div>
  );
}

export function ActionsPanel({ actions, escalated, escalationReason }: ActionsPanelProps) {
  if (!actions.length && !escalated) return null;

  return (
    <details className="actions-panel" open>
      <summary>
        <span>Policy actions</span>
        <ChevronDown />
      </summary>
      <div className="actions-content">
        <ActionChips actions={actions} />
        {escalated ? (
          <span
            className="action-chip action-escalated"
            title={escalationReason ?? "Escalated for supervisor review"}
          >
            <TriangleAlert /> Escalated to Supervisor
          </span>
        ) : null}
      </div>
    </details>
  );
}
