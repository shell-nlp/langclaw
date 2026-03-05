"use client";

import { useState, useEffect } from "react";
import { MessageSquare, MessageCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useActivityStore } from "@/stores/activity-store";
import { useZaloStore } from "@/stores/zalo-store";
import { ZaloSettingsDialog } from "@/components/zalo/zalo-settings-dialog";
import { cn } from "@/lib/utils";
import type { Campaign } from "@/types";

interface TopBarProps {
  campaign: Campaign;
  onChatToggle: () => void;
}

export function TopBar({ campaign, onChatToggle }: TopBarProps) {
  const { isScanning, latestScan } = useActivityStore();
  const { status, fetchStatus } = useZaloStore();
  const [zaloSettingsOpen, setZaloSettingsOpen] = useState(false);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const zaloConnected = status?.connected ?? false;

  const lastScanTime = latestScan?.completed_at || latestScan?.started_at;
  const formattedTime = lastScanTime
    ? new Date(lastScanTime + "Z").toLocaleString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
        day: "2-digit",
        month: "2-digit",
      })
    : null;

  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex items-center justify-between px-4 h-14">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold">{campaign.name}</h1>
          {isScanning ? (
            <Badge variant="default" className="text-xs animate-pulse">
              Đang quét...
            </Badge>
          ) : (
            <Badge variant="secondary" className="text-xs">
              Sẵn sàng
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-3">
          {formattedTime && (
            <span className="text-xs text-muted-foreground">
              Quét gần nhất: {formattedTime}
            </span>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setZaloSettingsOpen(true)}
            className="relative"
            title={zaloConnected ? "Zalo đã kết nối" : "Kết nối Zalo"}
          >
            <div className="relative">
              <MessageCircle className="h-4 w-4" />
              <span
                className={cn(
                  "absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full",
                  zaloConnected ? "bg-green-500" : "bg-red-500"
                )}
              />
            </div>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onChatToggle}
            className="relative"
          >
            <MessageSquare className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <ZaloSettingsDialog
        open={zaloSettingsOpen}
        onClose={() => setZaloSettingsOpen(false)}
      />
    </header>
  );
}
