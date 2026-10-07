"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

interface DateRangePickerProps {
  dateFrom: string;
  dateTo: string;
  onChange: (next: { dateFrom: string; dateTo: string }) => void;
}

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function DateRangePicker({
  dateFrom,
  dateTo,
  onChange,
}: DateRangePickerProps) {
  const presets: { label: string; days: number }[] = [
    { label: "7 days", days: 6 },
    { label: "30 days", days: 29 },
    { label: "90 days", days: 89 },
  ];

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="space-y-1.5">
        <Label htmlFor="date-from">From</Label>
        <Input
          id="date-from"
          type="date"
          value={dateFrom}
          max={dateTo}
          onChange={(e) => onChange({ dateFrom: e.target.value, dateTo })}
          className="w-[160px]"
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="date-to">To</Label>
        <Input
          id="date-to"
          type="date"
          value={dateTo}
          min={dateFrom}
          max={today()}
          onChange={(e) => onChange({ dateFrom, dateTo: e.target.value })}
          className="w-[160px]"
        />
      </div>
      <div className="flex gap-1">
        {presets.map((p) => (
          <Button
            key={p.label}
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              onChange({ dateFrom: isoDaysAgo(p.days), dateTo: today() })
            }
          >
            {p.label}
          </Button>
        ))}
      </div>
    </div>
  );
}
