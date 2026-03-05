"use client";

import { useListingStore } from "@/stores/listing-store";
import { PipelineColumn } from "./pipeline-column";
import { PIPELINE_STAGES } from "@/types";
import type { PipelineStage } from "@/types";

interface PipelineProps {
  campaignId: string;
}

export function Pipeline({ campaignId }: PipelineProps) {
  const { listings } = useListingStore();

  // Group listings by stage
  const byStage = PIPELINE_STAGES.reduce(
    (acc, stage) => {
      acc[stage.key] = listings.filter((l) => l.stage === stage.key);
      return acc;
    },
    {} as Record<PipelineStage, typeof listings>
  );

  return (
    <div className="h-full flex gap-3 overflow-x-auto pb-2">
      {PIPELINE_STAGES.map((stage) => (
        <PipelineColumn
          key={stage.key}
          stage={stage}
          listings={byStage[stage.key] || []}
          campaignId={campaignId}
        />
      ))}
    </div>
  );
}
