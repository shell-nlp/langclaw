"use client";

import { SearchQueryCard } from "./search-query-card";
import { ConnectionsSection } from "./connections-section";
import { ScheduleSection } from "./schedule-section";

interface SettingsScreenProps {
  campaignId: string;
  campaignPill?: React.ReactNode;
}

export function SettingsScreen({ campaignId, campaignPill }: SettingsScreenProps) {
  return (
    <div
      className="flex flex-col h-full overflow-y-auto"
      style={{ background: "var(--cream)", paddingBottom: 40 }}
    >
      {/* Header */}
      <div className="px-5 pt-4 pb-4">
        {/* Campaign pill */}
        <div className="mb-2">{campaignPill}</div>
        <h1
          className="text-[22px] font-extrabold"
          style={{ color: "var(--ink)", letterSpacing: "-0.8px" }}
        >
          Settings
        </h1>
      </div>

      <div className="px-5 space-y-6">
        {/* Section: Current search */}
        <div>
          <p
            className="text-[11px] font-semibold uppercase mb-2 px-1"
            style={{ color: "var(--ink-30)", letterSpacing: "0.8px" }}
          >
            Current search
          </p>
          <SearchQueryCard />
        </div>

        {/* Section: Connections */}
        <div>
          <p
            className="text-[11px] font-semibold uppercase mb-2 px-1"
            style={{ color: "var(--ink-30)", letterSpacing: "0.8px" }}
          >
            Connections
          </p>
          <ConnectionsSection />
        </div>

        {/* Schedules + research toggles */}
        <ScheduleSection campaignId={campaignId} />
      </div>
    </div>
  );
}
