import { Plane } from "lucide-react";
import { Message, MessageContent, MessageResponse } from "@/components/ai-elements/message";
import { ActionsPanel } from "./ActionsPanel";

export interface CaseMessage {
  id: string;
  role: "agent" | "skyresolve";
  content: string;
  actionsTaken?: string[];
  escalated?: boolean;
  escalationReason?: string | null;
}

export function MessageBubble({ message }: { message: CaseMessage }) {
  const isAgent = message.role === "agent";
  return (
    <Message
      className={`case-message ${isAgent ? "case-message-agent" : "case-message-skyresolve"}`}
      from={isAgent ? "user" : "assistant"}
    >
      <div className="message-label">
        {!isAgent ? <Plane aria-hidden="true" /> : null}
        {isAgent ? "Agent Input" : "SkyResolve"}
      </div>
      <MessageContent className="case-message-content">
        <MessageResponse>{message.content}</MessageResponse>
      </MessageContent>
      {!isAgent ? (
        <ActionsPanel
          actions={message.actionsTaken ?? []}
          escalated={message.escalated}
          escalationReason={message.escalationReason}
        />
      ) : null}
    </Message>
  );
}
