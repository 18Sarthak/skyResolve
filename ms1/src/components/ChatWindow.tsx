import type { KeyboardEvent } from "react";
import { Plane, Send, TriangleAlert } from "lucide-react";
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  PromptInput,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
} from "@/components/ai-elements/prompt-input";
import { Shimmer } from "@/components/ai-elements/shimmer";
import { MessageBubble, type CaseMessage } from "./MessageBubble";

interface ChatWindowProps {
  messages: CaseMessage[];
  draft: string;
  isLoading: boolean;
  isEscalated: boolean;
  error: string | null;
  onDraftChange: (value: string) => void;
  onSend: () => void;
}

export function ChatWindow({
  messages,
  draft,
  isLoading,
  isEscalated,
  error,
  onDraftChange,
  onSend,
}: ChatWindowProps) {
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      onSend();
    }
  };

  return (
    <div className="chat-shell">
      <Conversation className="chat-conversation">
        <ConversationContent className="chat-content">
          {messages.length ? (
            messages.map((message) => <MessageBubble key={message.id} message={message} />)
          ) : (
            <ConversationEmptyState
              className="chat-empty"
              icon={<Plane />}
              title="Ready for resolution"
              description="Select a customer and type their message to begin resolution."
            />
          )}
          {isLoading ? (
            <div className="processing-line">
              <Shimmer>SkyResolve is processing...</Shimmer>
            </div>
          ) : null}
        </ConversationContent>
        <ConversationScrollButton className="scroll-button" />
      </Conversation>

      <div className="composer-region">
        {isEscalated ? (
          <div className="escalation-banner" role="status">
            <TriangleAlert />
            <span>
              <strong>Supervisor review required.</strong> This case has been escalated to a human
              supervisor. The agent will not take further automated action.
            </span>
          </div>
        ) : null}
        <PromptInput className="case-composer" onSubmit={() => onSend()}>
          <PromptInputTextarea
            aria-label="Customer message"
            className="case-composer-textarea"
            disabled={isLoading || isEscalated}
            maxLength={4000}
            onChange={(event) => onDraftChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type the customer's message..."
            value={draft}
          />
          <PromptInputFooter className="composer-footer">
            <span>⌘ / Ctrl + Enter</span>
            <PromptInputSubmit
              disabled={isLoading || isEscalated || !draft.trim()}
              status={isLoading ? "submitted" : error ? "error" : "ready"}
            >
              {isLoading ? undefined : <Send />}
            </PromptInputSubmit>
          </PromptInputFooter>
        </PromptInput>
        {error ? (
          <p className="inline-error" role="alert">
            {error}
          </p>
        ) : null}
      </div>
    </div>
  );
}
