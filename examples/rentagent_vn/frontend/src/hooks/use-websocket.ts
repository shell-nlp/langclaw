"use client";

import { useEffect, useRef, useCallback } from "react";
import { WebSocketManager } from "@/lib/websocket";
import { useChatStore } from "@/stores/chat-store";

/**
 * Hook that manages the WebSocket connection lifecycle.
 * Connects on mount, disconnects on unmount. Routes incoming
 * messages to the chat store.
 */
export function useWebSocket(contextId: string) {
  const wsRef = useRef<WebSocketManager | null>(null);
  const { handleWSMessage, setWSStatus, addMessage, setTyping } = useChatStore();

  useEffect(() => {
    const ws = new WebSocketManager("web-user", contextId);
    wsRef.current = ws;

    ws.onMessage(handleWSMessage);
    ws.onStatus(setWSStatus);

    ws.connect();

    return () => {
      ws.disconnect();
      wsRef.current = null;
    };
  }, [contextId, handleWSMessage, setWSStatus]);

  const sendMessage = useCallback(
    (content: string) => {
      if (!wsRef.current) return;

      // Add user message to chat
      addMessage({
        id: `user-${Date.now()}`,
        role: "user",
        content,
        timestamp: new Date(),
      });

      // Send via WebSocket
      wsRef.current.send(content);
      setTyping(true);
    },
    [addMessage, setTyping]
  );

  return { sendMessage };
}
