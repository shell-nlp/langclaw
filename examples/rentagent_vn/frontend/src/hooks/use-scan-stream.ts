"use client";

import { useEffect, useRef } from "react";
import { useScanStreamStore } from "@/stores/scan-stream-store";
import type { ScanSSEEvent } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useScanStream(campaignId: string, scanId: string | null) {
  const { startStream, handleEvent, reset, setStatus } = useScanStreamStore();
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!scanId) {
      reset();
      return;
    }

    // Initialize store
    startStream(scanId);

    // Connect to SSE
    const url = `${BASE_URL}/api/v1/campaigns/${campaignId}/scans/${scanId}/stream`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setStatus("streaming");
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ScanSSEEvent;
        handleEvent(data);

        // Close connection on "done"
        if (data.type === "done") {
          eventSource.close();
          eventSourceRef.current = null;
        }
      } catch {
        console.error("Failed to parse scan SSE event:", event.data);
      }
    };

    eventSource.onerror = () => {
      // EventSource auto-reconnects on transient errors
      // If the scan completed, the server closes the stream
      console.warn("Scan SSE connection error or closed");
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [scanId, campaignId, startStream, handleEvent, reset, setStatus]);
}
