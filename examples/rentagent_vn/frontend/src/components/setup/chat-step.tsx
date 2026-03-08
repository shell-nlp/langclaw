"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { CampaignPreferences, WSOutbound } from "@/types";
import { WebSocketManager } from "@/lib/websocket";

interface ChatStepProps {
  onExtracted: (preferences: CampaignPreferences) => void;
}

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
}

const INITIAL_MESSAGE: Message = {
  id: "welcome",
  role: "assistant",
  content:
    "Chào bạn! Mình sẽ giúp bạn tìm phòng trọ. Bạn mô tả nhu cầu nhé — ví dụ: khu vực, số phòng ngủ, ngân sách, hoặc yêu cầu đặc biệt nào.",
};

export function ChatStep({ onExtracted }: ChatStepProps) {
  const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const wsRef = useRef<WebSocketManager | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleWSMessage = useCallback((msg: WSOutbound) => {
    if (msg.type === "pong") return;

    if (msg.type === "ai") {
      setMessages((prev) => [
        ...prev,
        {
          id: `ai-${Date.now()}`,
          role: "assistant",
          content: msg.content,
        },
      ]);
      setIsTyping(false);

      // Try to extract preferences from the AI message
      const prefs = tryExtractPreferences(msg.content);
      if (prefs) {
        // Small delay so user can read the message
        setTimeout(() => onExtracted(prefs), 1500);
      }
    } else if (msg.type === "tool_progress") {
      setMessages((prev) => [
        ...prev,
        {
          id: `prog-${Date.now()}`,
          role: "system",
          content: msg.content,
        },
      ]);
    }
  }, [onExtracted]);

  // Connect WebSocket
  useEffect(() => {
    const ws = new WebSocketManager("web-user", "setup");
    wsRef.current = ws;
    ws.onMessage(handleWSMessage);
    ws.connect();

    return () => {
      ws.disconnect();
      wsRef.current = null;
    };
  }, [handleWSMessage]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || !wsRef.current) return;

    setMessages((prev) => [
      ...prev,
      { id: `user-${Date.now()}`, role: "user", content: text },
    ]);
    setInput("");
    setIsTyping(true);
    wsRef.current.send(text);
  };

  const handleSkipChat = () => {
    // Allow user to skip chat and manually enter preferences
    onExtracted({});
  };

  return (
    <Card className="flex flex-col h-[500px]">
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold">Bạn cần tìm phòng thế nào?</h2>
        <p className="text-sm text-muted-foreground">
          Mô tả nhu cầu bằng tiếng Việt — mình sẽ hiểu và tóm tắt lại cho bạn.
        </p>
      </div>

      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-3">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : msg.role === "system"
                    ? "bg-muted text-muted-foreground text-xs italic"
                    : "bg-muted"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-lg px-3 py-2 text-sm">
                <span className="animate-pulse">Đang suy nghĩ...</span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="p-4 border-t">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="VD: Tìm phòng trọ Quận 7, 2PN, dưới 10 triệu..."
            disabled={isTyping}
          />
          <Button type="submit" size="icon" disabled={!input.trim() || isTyping}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
        <button
          onClick={handleSkipChat}
          className="mt-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Bỏ qua, tự nhập tiêu chí
        </button>
      </div>
    </Card>
  );
}

/**
 * Try to extract structured preferences from an AI message.
 * The agent should include a JSON block when it has enough info.
 */
function tryExtractPreferences(
  content: string
): CampaignPreferences | null {
  // Look for JSON block in the message
  const jsonMatch = content.match(/```json\s*([\s\S]*?)\s*```/);
  if (jsonMatch) {
    try {
      return JSON.parse(jsonMatch[1]);
    } catch {
      // Not valid JSON
    }
  }

  // Look for inline JSON object
  const inlineMatch = content.match(/\{[\s\S]*"district"[\s\S]*\}/);
  if (inlineMatch) {
    try {
      return JSON.parse(inlineMatch[0]);
    } catch {
      // Not valid JSON
    }
  }

  return null;
}
