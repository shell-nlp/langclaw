"use client";

import { useEffect, useState, useRef } from "react";
import { SetupWizard } from "@/components/setup/setup-wizard";
import { Dashboard } from "@/components/dashboard/dashboard";
import { useCampaignStore } from "@/stores/campaign-store";

export default function Home() {
  const { campaigns, fetchCampaigns } = useCampaignStore();
  const [activeCampaignId, setActiveCampaignId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  const fetchCampaignsRef = useRef(fetchCampaigns);
  fetchCampaignsRef.current = fetchCampaigns;

  useEffect(() => {
    fetchCampaignsRef.current().then(() => setReady(true));
  }, []); // Run once on mount

  // Once campaigns are loaded, auto-select the first active one
  useEffect(() => {
    if (!ready) return;
    if (activeCampaignId) return;

    const active = campaigns.find((c) => c.status === "active");
    if (active) {
      setActiveCampaignId(active.id);
    }
  }, [ready, campaigns, activeCampaignId]);

  // Show loading spinner only during initial campaign list fetch
  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-2">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-muted-foreground">Đang tải...</p>
        </div>
      </div>
    );
  }

  // No campaign? Show setup wizard
  if (!activeCampaignId) {
    return (
      <SetupWizard
        onComplete={(id) => {
          setActiveCampaignId(id);
        }}
      />
    );
  }

  // Dashboard
  return <Dashboard campaignId={activeCampaignId} />;
}
