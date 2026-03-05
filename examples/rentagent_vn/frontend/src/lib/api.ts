/**
 * REST API client for RentAgent VN backend.
 */

import type {
  Activity,
  Campaign,
  CampaignPreferences,
  CampaignStats,
  Listing,
  PipelineStage,
  Scan,
} from "@/types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Campaigns
// ---------------------------------------------------------------------------

export async function createCampaign(data: {
  name?: string;
  preferences?: CampaignPreferences;
  sources?: string[];
  scan_frequency?: string;
}): Promise<Campaign> {
  return request<Campaign>("/api/v1/campaigns", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listCampaigns(): Promise<Campaign[]> {
  return request<Campaign[]>("/api/v1/campaigns");
}

export async function getCampaign(id: string): Promise<Campaign> {
  return request<Campaign>(`/api/v1/campaigns/${id}`);
}

export async function updateCampaign(
  id: string,
  data: Partial<{
    name: string;
    preferences: CampaignPreferences;
    sources: string[];
    scan_frequency: string;
    status: string;
  }>
): Promise<Campaign> {
  return request<Campaign>(`/api/v1/campaigns/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// Listings
// ---------------------------------------------------------------------------

export async function getListings(
  campaignId: string,
  stage?: PipelineStage
): Promise<Listing[]> {
  const params = stage ? `?stage=${stage}` : "";
  return request<Listing[]>(
    `/api/v1/campaigns/${campaignId}/listings${params}`
  );
}

export async function getListing(
  campaignId: string,
  listingId: string
): Promise<Listing> {
  return request<Listing>(
    `/api/v1/campaigns/${campaignId}/listings/${listingId}`
  );
}

export async function updateListing(
  campaignId: string,
  listingId: string,
  data: {
    stage?: PipelineStage;
    skip_reason?: string;
    user_notes?: string;
  }
): Promise<Listing> {
  return request<Listing>(
    `/api/v1/campaigns/${campaignId}/listings/${listingId}`,
    { method: "PATCH", body: JSON.stringify(data) }
  );
}

// ---------------------------------------------------------------------------
// Scans
// ---------------------------------------------------------------------------

export async function triggerScan(
  campaignId: string,
  query?: string
): Promise<Scan> {
  return request<Scan>(`/api/v1/campaigns/${campaignId}/scan`, {
    method: "POST",
    body: JSON.stringify(query ? { query } : {}),
  });
}

export async function getScans(
  campaignId: string,
  limit = 10
): Promise<Scan[]> {
  return request<Scan[]>(
    `/api/v1/campaigns/${campaignId}/scans?limit=${limit}`
  );
}

// ---------------------------------------------------------------------------
// Activity
// ---------------------------------------------------------------------------

export async function getActivities(
  campaignId: string,
  limit = 50
): Promise<Activity[]> {
  return request<Activity[]>(
    `/api/v1/campaigns/${campaignId}/activity?limit=${limit}`
  );
}

// ---------------------------------------------------------------------------
// Stats
// ---------------------------------------------------------------------------

export async function getCampaignStats(
  campaignId: string
): Promise<CampaignStats> {
  return request<CampaignStats>(
    `/api/v1/campaigns/${campaignId}/stats`
  );
}
