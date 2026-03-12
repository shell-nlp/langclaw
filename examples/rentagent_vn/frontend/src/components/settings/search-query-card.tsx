"use client";

import { useCampaignStore } from "@/stores/campaign-store";

export function SearchQueryCard() {
  // Use selector to avoid subscribing to entire store
  const campaign = useCampaignStore((s) => s.campaign);
  const prefs = campaign?.preferences;

  const pills: string[] = [];
  if (prefs?.district) pills.push(prefs.district);
  if (prefs?.bedrooms) pills.push(`${prefs.bedrooms}BR`);
  if (prefs?.max_price)
    pills.push(`≤ ${Math.round(prefs.max_price / 1_000_000)}M`);
  if (prefs?.min_area) pills.push(`≥ ${prefs.min_area}m²`);

  return (
    <div
      className="flex items-start justify-between gap-3 p-4"
      style={{
        background: "var(--ds-white)",
        borderRadius: "var(--r-lg)",
        border: "1px solid var(--ink-08)",
      }}
    >
      <div className="flex flex-wrap gap-2 flex-1">
        {pills.length > 0 ? (
          pills.map((pill) => (
            <span
              key={pill}
              className="px-3 py-1 text-[12px] font-semibold"
              style={{
                background: "var(--terra-08)",
                color: "var(--terra)",
                borderRadius: "var(--r-full)",
              }}
            >
              {pill}
            </span>
          ))
        ) : (
          <span className="text-[13px]" style={{ color: "var(--ink-30)" }}>
            No search criteria set
          </span>
        )}
      </div>
      {/* TODO Phase 2: make interactive */}
      <button
        className="text-[13px] font-semibold flex-shrink-0"
        style={{ color: "var(--terra)" }}
        onClick={() => {}}
      >
        Edit
      </button>
    </div>
  );
}
