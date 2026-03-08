"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { SKIP_REASONS } from "@/types";

interface SkipDialogProps {
  open: boolean;
  onClose: () => void;
  onSkip: (reason: string) => Promise<void>;
}

export function SkipDialog({ open, onClose, onSkip }: SkipDialogProps) {
  const [selected, setSelected] = useState<string>(SKIP_REASONS[0].key);
  const [otherText, setOtherText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    const reason =
      selected === "other"
        ? otherText || "Khác"
        : SKIP_REASONS.find((r) => r.key === selected)?.label || selected;
    await onSkip(reason);
    setSubmitting(false);
    setSelected(SKIP_REASONS[0].key);
    setOtherText("");
  };

  return (
    <Dialog open={open} onOpenChange={() => onClose()}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Bỏ qua tin này?</DialogTitle>
        </DialogHeader>

        <RadioGroup
          value={selected}
          onValueChange={(v) => setSelected(v as typeof selected)}
          className="space-y-2"
        >
          {SKIP_REASONS.map((reason) => (
            <label
              key={reason.key}
              className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                selected === reason.key
                  ? "border-primary/30 bg-primary/5"
                  : "border-border"
              }`}
            >
              <RadioGroupItem value={reason.key} />
              <Label className="cursor-pointer text-sm">{reason.label}</Label>
            </label>
          ))}
        </RadioGroup>

        {selected === "other" && (
          <Input
            value={otherText}
            onChange={(e) => setOtherText(e.target.value)}
            placeholder="Lý do khác..."
            className="mt-2"
          />
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Hủy
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Đang lưu..." : "Bỏ qua"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
