"use client";

import * as React from "react";
import { Progress } from "@/components/ui/progress";

type Prosody = {
  sentence_id: number;
  segment_id?: number | null;
  speaking_rate_wpm?: number | null;
  pause_ratio?: number | null;
  rms_mean?: number | null;
};

function avg(nums: number[]) {
  if (!nums.length) return null;
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

export default function ProsodySummary({
  prosody,
  segments,
}: {
  prosody: Prosody[];
  segments: any[];
}) {
  const sentenceToSeg = React.useMemo(() => {
    const m = new Map<number, number>();
    (segments || []).forEach((seg, segIndex) => {
      (seg.sentence_ids || []).forEach((sid: number) => m.set(sid, segIndex));
    });
    return m;
  }, [segments]);

  const enriched = prosody.map((p) => ({
    ...p,
    segIndex: p.segment_id ?? sentenceToSeg.get(p.sentence_id) ?? null,
  }));

  const overallRate = avg(enriched.map(p => p.speaking_rate_wpm).filter((x): x is number => typeof x === "number"));
  const overallPause = avg(enriched.map(p => p.pause_ratio).filter((x): x is number => typeof x === "number"));

  // crude scaling for progress bars (you can tweak)
  const ratePct = overallRate == null ? 0 : Math.max(0, Math.min(100, (overallRate / 220) * 100));
  const pausePct = overallPause == null ? 0 : Math.max(0, Math.min(100, overallPause * 100));

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="text-xs text-zinc-500">Speaking rate (avg)</div>
        <div className="flex items-center justify-between text-sm">
          <span>{overallRate == null ? "—" : `${overallRate.toFixed(0)} wpm`}</span>
          <span className="text-xs text-zinc-500">0–220</span>
        </div>
        <Progress value={ratePct} />
      </div>

      <div className="space-y-2">
        <div className="text-xs text-zinc-500">Pause ratio (avg)</div>
        <div className="flex items-center justify-between text-sm">
          <span>{overallPause == null ? "—" : `${(overallPause * 100).toFixed(0)}%`}</span>
          <span className="text-xs text-zinc-500">0–100%</span>
        </div>
        <Progress value={pausePct} />
      </div>

      <div className="text-xs text-zinc-500">
        Prosody is computed per sentence; segment grouping is inferred from segment.sentence_ids.
      </div>
    </div>
  );
}
