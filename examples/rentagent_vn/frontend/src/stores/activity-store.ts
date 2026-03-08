import { create } from "zustand";
import type { Activity, Scan } from "@/types";
import * as api from "@/lib/api";

interface ActivityState {
  activities: Activity[];
  scans: Scan[];
  latestScan: Scan | null;
  isScanning: boolean;
  unreadCount: number;
  loading: boolean;

  // Actions
  fetchActivities: (campaignId: string) => Promise<void>;
  fetchScans: (campaignId: string) => Promise<void>;
  triggerScan: (campaignId: string, query?: string) => Promise<Scan>;
  addActivity: (activity: Activity) => void;
  markRead: () => void;
  setScanning: (scanning: boolean) => void;
}

export const useActivityStore = create<ActivityState>((set, get) => ({
  activities: [],
  scans: [],
  latestScan: null,
  isScanning: false,
  unreadCount: 0,
  loading: false,

  fetchActivities: async (campaignId) => {
    set({ loading: true });
    try {
      const activities = await api.getActivities(campaignId);
      set({ activities, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchScans: async (campaignId) => {
    try {
      const scans = await api.getScans(campaignId);
      const latestScan = scans[0] || null;
      const isScanning = latestScan?.status === "running";
      set({ scans, latestScan, isScanning });
    } catch {
      // Silently fail
    }
  },

  triggerScan: async (campaignId, query) => {
    set({ isScanning: true });
    try {
      const scan = await api.triggerScan(campaignId, query);
      set((s) => ({
        scans: [scan, ...s.scans],
        latestScan: scan,
      }));
      return scan;
    } catch (e) {
      set({ isScanning: false });
      throw e;
    }
  },

  addActivity: (activity) =>
    set((s) => ({
      activities: [activity, ...s.activities],
      unreadCount: s.unreadCount + 1,
    })),

  markRead: () => set({ unreadCount: 0 }),
  setScanning: (isScanning) => set({ isScanning }),
}));
