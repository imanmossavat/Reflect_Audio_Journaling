"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

interface SegmentationConfigProps {
    percentile: number;
    minSize: number;
    onChange: (key: string, value: number) => void;
}

export default function SegmentationConfig({ percentile, minSize, onChange }: SegmentationConfigProps) {
    return (
        <Card className="border-zinc-200 dark:border-zinc-800 shadow-none">
            <CardHeader><CardTitle className="text-sm font-semibold">Segmentation</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase">Percentile</label>
                    <Input type="number" value={percentile || 0} onChange={(e) => onChange('SEGMENTATION_PERCENTILE', parseInt(e.target.value))} />
                </div>
                <div className="space-y-2">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase">Min Size</label>
                    <Input type="number" value={minSize || 0} onChange={(e) => onChange('SEGMENTATION_MIN_SIZE', parseInt(e.target.value))} />
                </div>
            </CardContent>
        </Card>
    );
}
