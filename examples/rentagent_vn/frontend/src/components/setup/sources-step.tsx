"use client";

import { useState } from "react";
import { ArrowLeft, ArrowRight, Plus, X, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface SourcesStepProps {
  onConfirm: (sources: string[]) => void;
  onBack: () => void;
}

const DEFAULT_SOURCES = [
  {
    url: "https://www.nhatot.com/thue-phong-tro",
    label: "Nhà Tốt",
    enabled: true,
  },
  {
    url: "https://batdongsan.com.vn/cho-thue",
    label: "Batdongsan.com.vn",
    enabled: true,
  },
];

export function SourcesStep({ onConfirm, onBack }: SourcesStepProps) {
  const [defaults, setDefaults] = useState(DEFAULT_SOURCES);
  const [customUrls, setCustomUrls] = useState<string[]>([]);
  const [urlInput, setUrlInput] = useState("");
  const [error, setError] = useState("");

  const toggleDefault = (index: number) => {
    setDefaults((prev) =>
      prev.map((s, i) => (i === index ? { ...s, enabled: !s.enabled } : s))
    );
  };

  const addUrl = () => {
    const url = urlInput.trim();
    if (!url) return;

    // Basic validation
    if (!url.startsWith("http")) {
      setError("URL must start with http:// or https://");
      return;
    }
    if (customUrls.includes(url)) {
      setError("This URL has already been added");
      return;
    }

    setCustomUrls((prev) => [...prev, url]);
    setUrlInput("");
    setError("");
  };

  const removeUrl = (url: string) => {
    setCustomUrls((prev) => prev.filter((u) => u !== url));
  };

  const handleConfirm = () => {
    const sources = [
      ...defaults.filter((s) => s.enabled).map((s) => s.url),
      ...customUrls,
    ];
    onConfirm(sources);
  };

  const totalSources =
    defaults.filter((s) => s.enabled).length + customUrls.length;

  return (
    <Card className="p-6">
      <div className="mb-6">
        <h2 className="text-lg font-semibold">Select search sources</h2>
        <p className="text-sm text-muted-foreground">
          Add Facebook group links or rental listing websites.
        </p>
      </div>

      {/* Default sources */}
      <div className="space-y-2 mb-6">
        <p className="text-sm font-medium text-muted-foreground">
          Default sources
        </p>
        {defaults.map((source, i) => (
          <button
            key={source.url}
            onClick={() => toggleDefault(i)}
            className={`w-full flex items-center gap-3 p-3 rounded-lg border text-left transition-colors ${
              source.enabled
                ? "border-primary/30 bg-primary/5"
                : "border-border opacity-50"
            }`}
          >
            <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">{source.label}</p>
              <p className="text-xs text-muted-foreground truncate">
                {source.url}
              </p>
            </div>
            <div
              className={`w-4 h-4 rounded border-2 transition-colors ${
                source.enabled
                  ? "bg-primary border-primary"
                  : "border-muted-foreground"
              }`}
            />
          </button>
        ))}
      </div>

      {/* Custom URLs */}
      <div className="space-y-2 mb-6">
        <p className="text-sm font-medium text-muted-foreground">
          Add other sources (Facebook groups, forums...)
        </p>
        {customUrls.map((url) => (
          <div
            key={url}
            className="flex items-center gap-2 p-2 rounded-lg border bg-muted/50"
          >
            <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
            <span className="text-sm flex-1 truncate">{url}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => removeUrl(url)}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        ))}
        <div className="flex gap-2">
          <Input
            value={urlInput}
            onChange={(e) => {
              setUrlInput(e.target.value);
              setError("");
            }}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addUrl())}
            placeholder="https://www.facebook.com/groups/..."
          />
          <Button
            variant="outline"
            size="icon"
            onClick={addUrl}
            disabled={!urlInput.trim()}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>

      <div className="flex justify-between">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <Button onClick={handleConfirm} disabled={totalSources === 0}>
          <ArrowRight className="h-4 w-4 mr-1" />
          Next ({totalSources} sources)
        </Button>
      </div>
    </Card>
  );
}
