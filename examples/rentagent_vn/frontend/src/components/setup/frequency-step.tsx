"use client";

import { useState } from "react";
import { ArrowLeft, Rocket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";

interface FrequencyStepProps {
  onConfirm: (frequency: string) => void;
  onBack: () => void;
}

const FREQUENCIES = [
  {
    value: "manual",
    label: "Thủ công",
    description: "Quét khi bạn bấm nút. Phù hợp nếu không vội.",
  },
  {
    value: "1x_day",
    label: "1 lần/ngày",
    description: "Quét tự động mỗi sáng lúc 8:00.",
  },
  {
    value: "2x_day",
    label: "2 lần/ngày",
    description: "Quét lúc 8:00 và 18:00. Không bỏ lỡ tin mới.",
  },
];

export function FrequencyStep({ onConfirm, onBack }: FrequencyStepProps) {
  const [selected, setSelected] = useState("manual");
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    setLoading(true);
    await onConfirm(selected);
  };

  return (
    <Card className="p-6">
      <div className="mb-6">
        <h2 className="text-lg font-semibold">Tần suất quét</h2>
        <p className="text-sm text-muted-foreground">
          Chọn mức độ tự động tìm kiếm. Bạn luôn có thể quét thủ công.
        </p>
      </div>

      <RadioGroup
        value={selected}
        onValueChange={setSelected}
        className="space-y-3"
      >
        {FREQUENCIES.map((freq) => (
          <label
            key={freq.value}
            className={`flex items-start gap-3 p-4 rounded-lg border cursor-pointer transition-colors ${
              selected === freq.value
                ? "border-primary/30 bg-primary/5"
                : "border-border hover:bg-muted/50"
            }`}
          >
            <RadioGroupItem value={freq.value} className="mt-0.5" />
            <div>
              <p className="text-sm font-medium">{freq.label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {freq.description}
              </p>
            </div>
          </label>
        ))}
      </RadioGroup>

      <div className="flex justify-between mt-6">
        <Button variant="ghost" onClick={onBack} disabled={loading}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Quay lại
        </Button>
        <Button onClick={handleConfirm} disabled={loading}>
          {loading ? (
            <span className="animate-pulse">Đang tạo...</span>
          ) : (
            <>
              <Rocket className="h-4 w-4 mr-1" />
              Bắt đầu
            </>
          )}
        </Button>
      </div>
    </Card>
  );
}
