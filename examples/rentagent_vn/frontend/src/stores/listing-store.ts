import { create } from "zustand";
import type { Listing, PipelineStage } from "@/types";
import * as api from "@/lib/api";

interface ListingState {
  listings: Listing[];
  selectedListing: Listing | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchListings: (campaignId: string, stage?: PipelineStage) => Promise<void>;
  updateStage: (
    campaignId: string,
    listingId: string,
    stage: PipelineStage,
    skipReason?: string
  ) => Promise<void>;
  updateNotes: (campaignId: string, listingId: string, notes: string) => Promise<void>;
  selectListing: (listing: Listing | null) => void;
  clearError: () => void;
}

export const useListingStore = create<ListingState>((set) => ({
  listings: [],
  selectedListing: null,
  loading: false,
  error: null,

  fetchListings: async (campaignId, stage) => {
    set({ loading: true, error: null });
    try {
      const listings = await api.getListings(campaignId, stage);
      set({ listings, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  updateStage: async (campaignId, listingId, stage, skipReason) => {
    try {
      const updated = await api.updateListing(campaignId, listingId, {
        stage,
        skip_reason: skipReason,
      });
      set((s) => ({
        listings: s.listings.map((l) => (l.id === listingId ? updated : l)),
        selectedListing:
          s.selectedListing?.id === listingId ? updated : s.selectedListing,
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  updateNotes: async (campaignId, listingId, notes) => {
    try {
      const updated = await api.updateListing(campaignId, listingId, {
        user_notes: notes,
      });
      set((s) => ({
        listings: s.listings.map((l) => (l.id === listingId ? updated : l)),
        selectedListing:
          s.selectedListing?.id === listingId ? updated : s.selectedListing,
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  selectListing: (listing) => set({ selectedListing: listing }),
  clearError: () => set({ error: null }),
}));
