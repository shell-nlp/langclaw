"use client";

import { useState } from "react";
import type { CampaignPreferences } from "@/types";
import { useCampaignStore } from "@/stores/campaign-store";
import { toast } from "sonner";
import { ChatStep } from "./chat-step";
import { ConfirmStep } from "./confirm-step";
import { SourcesStep } from "./sources-step";
import { FrequencyStep } from "./frequency-step";

type Step = "chat" | "confirm" | "sources" | "frequency";

interface SetupWizardProps {
  onComplete: (campaignId: string) => void;
}

export function SetupWizard({ onComplete }: SetupWizardProps) {
  const [step, setStep] = useState<Step>("chat");
  const [preferences, setPreferences] = useState<CampaignPreferences>({});
  const [sources, setSources] = useState<string[]>([]);
  const [frequency, setFrequency] = useState("manual");
  const { createCampaign } = useCampaignStore();

  const handlePreferencesExtracted = (prefs: CampaignPreferences) => {
    setPreferences(prefs);
    setStep("confirm");
  };

  const handlePreferencesConfirmed = (prefs: CampaignPreferences) => {
    setPreferences(prefs);
    setStep("sources");
  };

  const handleSourcesConfirmed = (urls: string[]) => {
    setSources(urls);
    setStep("frequency");
  };

  const handleFrequencyConfirmed = async (freq: string) => {
    setFrequency(freq);
    try {
      const campaign = await createCampaign({
        name: buildCampaignName(preferences),
        preferences,
        sources,
        scan_frequency: freq,
      });
      onComplete(campaign.id);
    } catch (e) {
      console.error("Failed to create campaign:", e);
      toast.error("Failed to create campaign. Check if backend is running.");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-2xl">
        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {(["chat", "confirm", "sources", "frequency"] as Step[]).map(
            (s, i) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                    step === s
                      ? "bg-primary text-primary-foreground"
                      : i <
                        ["chat", "confirm", "sources", "frequency"].indexOf(step)
                      ? "bg-primary/20 text-primary"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {i + 1}
                </div>
                {i < 3 && (
                  <div className="w-8 h-px bg-border" />
                )}
              </div>
            )
          )}
        </div>

        {step === "chat" && (
          <ChatStep onExtracted={handlePreferencesExtracted} />
        )}
        {step === "confirm" && (
          <ConfirmStep
            preferences={preferences}
            onConfirm={handlePreferencesConfirmed}
            onBack={() => setStep("chat")}
          />
        )}
        {step === "sources" && (
          <SourcesStep
            onConfirm={handleSourcesConfirmed}
            onBack={() => setStep("confirm")}
          />
        )}
        {step === "frequency" && (
          <FrequencyStep
            onConfirm={handleFrequencyConfirmed}
            onBack={() => setStep("sources")}
          />
        )}
      </div>
    </div>
  );
}

function buildCampaignName(prefs: CampaignPreferences): string {
  const parts: string[] = [];
  if (prefs.property_type) parts.push(prefs.property_type);
  if (prefs.district) parts.push(prefs.district);
  if (prefs.bedrooms) parts.push(`${prefs.bedrooms}BR`);
  return parts.length > 0 ? parts.join(" · ") : "New Campaign";
}
