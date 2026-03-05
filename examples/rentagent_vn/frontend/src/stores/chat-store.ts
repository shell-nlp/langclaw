import { create } from "zustand";
import type { ChatMessage, WSOutbound } from "@/types";

interface ChatState {
  messages: ChatMessage[];
  isTyping: boolean;
  wsStatus: "connecting" | "connected" | "disconnected";

  // Actions
  addMessage: (msg: ChatMessage) => void;
  handleWSMessage: (msg: WSOutbound) => void;
  setWSStatus: (status: ChatState["wsStatus"]) => void;
  setTyping: (typing: boolean) => void;
  clear: () => void;
}

let msgCounter = 0;
function nextId() {
  return `msg-${Date.now()}-${++msgCounter}`;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isTyping: false,
  wsStatus: "disconnected",

  addMessage: (msg) =>
    set((s) => ({ messages: [...s.messages, msg] })),

  handleWSMessage: (msg) => {
    if (msg.type === "pong") return;

    if (msg.type === "ai") {
      set((s) => ({
        messages: [
          ...s.messages,
          {
            id: nextId(),
            role: "assistant" as const,
            content: msg.content,
            timestamp: new Date(),
          },
        ],
        isTyping: false,
      }));
    } else if (msg.type === "tool_progress") {
      set((s) => ({
        messages: [
          ...s.messages,
          {
            id: nextId(),
            role: "system" as const,
            content: msg.content,
            timestamp: new Date(),
            metadata: msg.metadata,
          },
        ],
      }));
    } else if (msg.type === "tool_result") {
      // Tool results are typically followed by an AI message
      // Don't show raw tool results to the user
    } else if (msg.type === "error") {
      set((s) => ({
        messages: [
          ...s.messages,
          {
            id: nextId(),
            role: "system" as const,
            content: msg.content,
            timestamp: new Date(),
          },
        ],
        isTyping: false,
      }));
    }
  },

  setWSStatus: (wsStatus) => set({ wsStatus }),
  setTyping: (isTyping) => set({ isTyping }),
  clear: () => set({ messages: [], isTyping: false }),
}));
