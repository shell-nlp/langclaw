import { create } from "zustand";
import type { Campaign, CampaignStats } from "@/types";
import * as api from "@/lib/api";

interface CampaignState {
  campaign: Campaign | null;
  campaigns: Campaign[];
  stats: CampaignStats | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchCampaigns: () => Promise<void>;
  fetchCampaign: (id: string) => Promise<void>;
  fetchStats: (id: string) => Promise<void>;
  createCampaign: (data: Parameters<typeof api.createCampaign>[0]) => Promise<Campaign>;
  updateCampaign: (id: string, data: Parameters<typeof api.updateCampaign>[1]) => Promise<void>;
  setCampaign: (campaign: Campaign | null) => void;
  clearError: () => void;
}

export const useCampaignStore = create<CampaignState>((set, get) => ({
  campaign: null,
  campaigns: [],
  stats: null,
  loading: false,
  error: null,

  fetchCampaigns: async () => {
    set({ loading: true, error: null });
    try {
      const campaigns = await api.listCampaigns();
      set({ campaigns, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchCampaign: async (id) => {
    // Only show loading state on the very first fetch (no campaign yet).
    // Subsequent refetches update silently to avoid triggering parent
    // re-renders that would unmount/remount the Dashboard.
    if (!get().campaign) {
      set({ loading: true, error: null });
    }
    try {
      const campaign = await api.getCampaign(id);
      set({ campaign, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchStats: async (id) => {
    try {
      const stats = await api.getCampaignStats(id);
      set({ stats });
    } catch (e) {
      console.error("Failed to fetch stats:", e);
    }
  },

  createCampaign: async (data) => {
    set({ loading: true, error: null });
    try {
      const campaign = await api.createCampaign(data);
      set((s) => ({
        campaign,
        campaigns: [campaign, ...s.campaigns],
        loading: false,
      }));
      return campaign;
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  updateCampaign: async (id, data) => {
    try {
      const campaign = await api.updateCampaign(id, data);
      set((s) => ({
        campaign: s.campaign?.id === id ? campaign : s.campaign,
        campaigns: s.campaigns.map((c) => (c.id === id ? campaign : c)),
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  setCampaign: (campaign) => set({ campaign }),
  clearError: () => set({ error: null }),
}));
