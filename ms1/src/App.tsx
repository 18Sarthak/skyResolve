import { useMemo, useRef, useState } from "react";
import { getHistory, sendMessage, type HistoryTurn } from "@/api";
import { CUSTOMERS, DEFAULT_CUSTOMER } from "@/data/customers";
import { Sidebar } from "@/components/Sidebar";
import { CaseHeader } from "@/components/CaseHeader";
import { ChatWindow } from "@/components/ChatWindow";
import { HistoryDrawer } from "@/components/HistoryDrawer";
import type { CaseMessage } from "@/components/MessageBubble";

const BACKEND_ERROR = "Failed to reach SkyResolve backend. Is the server running?";

type MessagesByPnr = Record<string, CaseMessage[]>;
type BooleanByPnr = Record<string, boolean>;
type StringByPnr = Record<string, string>;
type ErrorByPnr = Record<string, string | null>;

const emptyMessages = () =>
  Object.fromEntries(CUSTOMERS.map(({ pnr }) => [pnr, []])) as MessagesByPnr;
const emptyBooleans = () =>
  Object.fromEntries(CUSTOMERS.map(({ pnr }) => [pnr, false])) as BooleanByPnr;
const emptyStrings = () => Object.fromEntries(CUSTOMERS.map(({ pnr }) => [pnr, ""])) as StringByPnr;
const emptyErrors = () => Object.fromEntries(CUSTOMERS.map(({ pnr }) => [pnr, null])) as ErrorByPnr;

export default function App() {
  const [selectedPnr, setSelectedPnr] = useState(DEFAULT_CUSTOMER.pnr);
  const [messages, setMessages] = useState<MessagesByPnr>(emptyMessages);
  const [loading, setLoading] = useState<BooleanByPnr>(emptyBooleans);
  const [escalated, setEscalated] = useState<BooleanByPnr>(emptyBooleans);
  const [drafts, setDrafts] = useState<StringByPnr>(emptyStrings);
  const [errors, setErrors] = useState<ErrorByPnr>(emptyErrors);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyTurns, setHistoryTurns] = useState<HistoryTurn[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const customer = useMemo(
    () => CUSTOMERS.find((item) => item.pnr === selectedPnr) ?? DEFAULT_CUSTOMER,
    [selectedPnr],
  );

  const showToast = (message: string) => {
    setToast(message);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 4500);
  };

  const handleSend = async () => {
    const message = drafts[selectedPnr]?.trim();
    if (!message || loading[selectedPnr] || escalated[selectedPnr]) return;

    setLoading((current) => ({ ...current, [selectedPnr]: true }));
    setErrors((current) => ({ ...current, [selectedPnr]: null }));

    try {
      const response = await sendMessage(selectedPnr, message);
      const stamp = Date.now();
      setMessages((current) => ({
        ...current,
        [selectedPnr]: [
          ...(current[selectedPnr] ?? []),
          { id: `agent-${stamp}`, role: "agent", content: message },
          {
            id: `skyresolve-${stamp}`,
            role: "skyresolve",
            content: response.response,
            actionsTaken: response.actions_taken,
            escalated: response.escalated,
            escalationReason: response.escalation_reason,
          },
        ],
      }));
      setDrafts((current) => ({ ...current, [selectedPnr]: "" }));
      if (response.escalated) setEscalated((current) => ({ ...current, [selectedPnr]: true }));
    } catch {
      setErrors((current) => ({ ...current, [selectedPnr]: BACKEND_ERROR }));
      showToast(BACKEND_ERROR);
    } finally {
      setLoading((current) => ({ ...current, [selectedPnr]: false }));
    }
  };

  const openHistory = async () => {
    setHistoryOpen(true);
    setHistoryLoading(true);
    setHistoryError(null);
    setHistoryTurns([]);
    try {
      const turns = await getHistory(selectedPnr);
      setHistoryTurns(
        [...turns].sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
        ),
      );
    } catch {
      setHistoryError(BACKEND_ERROR);
    } finally {
      setHistoryLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <Sidebar selectedPnr={selectedPnr} onSelect={setSelectedPnr} onOpenHistory={openHistory} />
      <main className="case-workspace">
        <CaseHeader customer={customer} escalated={escalated[selectedPnr] ?? false} />
        <ChatWindow
          messages={messages[selectedPnr] ?? []}
          draft={drafts[selectedPnr] ?? ""}
          isLoading={loading[selectedPnr] ?? false}
          isEscalated={escalated[selectedPnr] ?? false}
          error={errors[selectedPnr] ?? null}
          onDraftChange={(value) => setDrafts((current) => ({ ...current, [selectedPnr]: value }))}
          onSend={handleSend}
        />
      </main>
      <HistoryDrawer
        open={historyOpen}
        customer={customer}
        turns={historyTurns}
        loading={historyLoading}
        error={historyError}
        onClose={() => setHistoryOpen(false)}
      />
      {toast ? (
        <div className="error-toast" role="alert">
          {toast}
        </div>
      ) : null}
    </div>
  );
}
