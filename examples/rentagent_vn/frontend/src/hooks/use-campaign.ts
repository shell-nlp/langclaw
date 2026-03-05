"use client";

import { useEffect, useRef } from "react";
import { useCampaignStore } from "@/stores/campaign-store";
import { useListingStore } from "@/stores/listing-store";
import { useActivityStore } from "@/stores/activity-store";

/**
 * Hook that loads campaign data on mount and sets up polling.
 * Uses refs to avoid re-running the effect when store functions change.
 *
 * Polling strategy:
 * - Always checks scan status (lightweight) every 5s
 * - Only fetches stats/listings/activities when a scan is actively running
 */
export function useCampaign(campaignId: string | null) {
  const campaignStore = useCampaignStore();
  const listingStore = useListingStore();
  const activityStore = useActivityStore();

  // Store all functions in refs to keep effect dependencies minimal
  const storesRef = useRef({ campaignStore, listingStore, activityStore });
  storesRef.current = { campaignStore, listingStore, activityStore };

  useEffect(() => {
    if (!campaignId) return;

    const { campaignStore, listingStore, activityStore } = storesRef.current;

    // Initial fetch — load everything once
    campaignStore.fetchCampaign(campaignId);
    campaignStore.fetchStats(campaignId);
    listingStore.fetchListings(campaignId);
    activityStore.fetchScans(campaignId);
    activityStore.fetchActivities(campaignId);

    // Poll: always check scan status; only fetch heavy data while scanning
    const interval = setInterval(() => {
      const { campaignStore, activityStore, listingStore } = storesRef.current;
      // Always check scan status (lightweight endpoint)
      activityStore.fetchScans(campaignId);
      // Only fetch heavy data when a scan is actively running
      if (activityStore.isScanning) {
        campaignStore.fetchStats(campaignId);
        listingStore.fetchListings(campaignId);
        activityStore.fetchActivities(campaignId);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [campaignId]); // Only re-run when campaignId changes
}
