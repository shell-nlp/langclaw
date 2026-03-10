"use client";

import { useState } from "react";
import { ArrowLeft, Check, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import type { CampaignPreferences } from "@/types";

interface ConfirmStepProps {
  preferences: CampaignPreferences;
  onConfirm: (prefs: CampaignPreferences) => void;
  onBack: () => void;
}

const PREF_FIELDS: {
  key: string;
  label: string;
  placeholder: string;
  type?: string;
}[] = [
  { key: "district", label: "Area", placeholder: "e.g. District 7, Binh Thanh" },
  { key: "property_type", label: "Property type", placeholder: "e.g. Apartment, room, studio" },
  {
    key: "bedrooms",
    label: "Bedrooms",
    placeholder: "e.g. 2",
    type: "number",
  },
  {
    key: "min_price",
    label: "Min price (VND)",
    placeholder: "e.g. 5000000",
    type: "number",
  },
  {
    key: "max_price",
    label: "Max price (VND)",
    placeholder: "e.g. 15000000",
    type: "number",
  },
  {
    key: "min_area",
    label: "Min area (m²)",
    placeholder: "e.g. 30",
    type: "number",
  },
  { key: "notes", label: "Additional notes", placeholder: "e.g. Has balcony, near school..." },
];

export function ConfirmStep({
  preferences,
  onConfirm,
  onBack,
}: ConfirmStepProps) {
  const [prefs, setPrefs] = useState<CampaignPreferences>({ ...preferences });
  const [editing, setEditing] = useState<string | null>(null);
  const [inputValues, setInputValues] = useState<Record<string, string>>(
    Object.fromEntries(PREF_FIELDS.map((f) => [f.key, String(preferences[f.key] ?? "")]))
  );

  const commitField = (key: string) => {
    const field = PREF_FIELDS.find((f) => f.key === key)!;
    const raw = inputValues[key];
    const value = field.type === "number" ? Number(raw) || "" : raw;
    setPrefs((prev) => ({ ...prev, [key]: value || undefined }));
    setEditing(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, key: string) => {
    if (e.key === "Enter") {
      e.preventDefault();
      commitField(key);
    }
  };

  const filledFields = PREF_FIELDS.filter(
    (f) => prefs[f.key] !== undefined && prefs[f.key] !== ""
  );
  const emptyFields = PREF_FIELDS.filter(
    (f) => prefs[f.key] === undefined || prefs[f.key] === ""
  );

  return (
    <Card className="p-6">
      <div className="mb-6">
        <h2 className="text-lg font-semibold">Confirm criteria</h2>
        <p className="text-sm text-muted-foreground">
          Review and edit if needed. You can change this later.
        </p>
      </div>

      <div className="space-y-4">
        {/* Filled preferences as chips */}
        {filledFields.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {filledFields.map((field) => (
              <Badge
                key={field.key}
                variant="secondary"
                className="cursor-pointer hover:bg-accent text-sm py-1 px-3"
                onClick={() => {
                  setInputValues((prev) => ({ ...prev, [field.key]: String(prefs[field.key] ?? "") }));
                  setEditing(editing === field.key ? null : field.key);
                }}
              >
                {field.label}: {String(prefs[field.key])}
                <Pencil className="h-3 w-3 ml-1" />
              </Badge>
            ))}
          </div>
        )}

        {/* Edit fields */}
        {PREF_FIELDS.map((field) => (
          <div
            key={field.key}
            className={
              editing === field.key || emptyFields.includes(field)
                ? "block"
                : "hidden"
            }
          >
            <Label htmlFor={field.key} className="text-sm mb-1.5">
              {field.label}
            </Label>
            <Input
              id={field.key}
              type={field.type || "text"}
              value={inputValues[field.key] ?? ""}
              onChange={(e) =>
                setInputValues((prev) => ({ ...prev, [field.key]: e.target.value }))
              }
              onKeyDown={(e) => handleKeyDown(e, field.key)}
              onBlur={() => commitField(field.key)}
              placeholder={field.placeholder}
            />
          </div>
        ))}
      </div>

      <div className="flex justify-between mt-6">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <Button onClick={() => onConfirm(prefs)}>
          <Check className="h-4 w-4 mr-1" />
          Confirm
        </Button>
      </div>
    </Card>
  );
}
