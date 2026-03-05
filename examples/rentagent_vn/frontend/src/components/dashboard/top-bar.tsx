"use client";

import { MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useActivityStore } from "@/stores/activity-store";
import type { Campaign } from "@/types";

interface TopBarProps {
  campaign: Campaign;
  onChatToggle: () => void;
}

export function TopBar({ campaign, onChatToggle }: TopBarProps) {
  const { isScanning, latestScan } = useActivityStore();

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
            onClick={onChatToggle}
            className="relative"
          >
            <MessageSquare className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
