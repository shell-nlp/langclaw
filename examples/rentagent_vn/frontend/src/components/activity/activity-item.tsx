"use client";

import { CheckCircle2, AlertCircle, Loader2, Search } from "lucide-react";
import type { Activity } from "@/types";

interface ActivityItemProps {
  activity: Activity;
}

const EVENT_ICONS: Record<string, React.ReactNode> = {
  scan_start: <Search className="h-3.5 w-3.5 text-blue-500" />,
  progress: <Loader2 className="h-3.5 w-3.5 text-yellow-500" />,
  scan_end: <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />,
  result: <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />,
  error: <AlertCircle className="h-3.5 w-3.5 text-destructive" />,
};

export function ActivityItem({ activity }: ActivityItemProps) {
  const icon = EVENT_ICONS[activity.event_type] || (
    <Loader2 className="h-3.5 w-3.5 text-muted-foreground" />
  );

  const time = new Date(activity.created_at + "Z").toLocaleTimeString(
    "vi-VN",
    { hour: "2-digit", minute: "2-digit" }
  );

  return (
    <div className="flex gap-2.5 text-sm">
      <div className="mt-0.5 shrink-0">{icon}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm">{activity.message}</p>
        <time className="text-[11px] text-muted-foreground">{time}</time>
      </div>
    </div>
  );
}
