"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Line, LineChart, ResponsiveContainer, Tooltip } from "recharts";

interface ConfidenceTrendProps {
    data: { id: string; confidence: number }[];
}

export default function ConfidenceTrend({ data }: ConfidenceTrendProps) {
    if (!data || data.length === 0) return null;

    // Latest 20 only to keep chart clean
    const displayData = data.slice(0, 20).reverse();

    return (
        <Card className="col-span-4 md:col-span-2 border-zinc-200 dark:border-zinc-800 shadow-sm">
            <CardHeader>
                <CardTitle>Model Quality</CardTitle>
                <CardDescription>Confidence score per recording (last 20)</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="h-[250px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={displayData}>
                            <Tooltip
                                contentStyle={{ background: "#27272a", border: "none", color: "#fff", borderRadius: "8px", fontSize: "12px" }}
                                cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 2 }}
                            />
                            <Line
                                type="monotone"
                                dataKey="confidence"
                                stroke="#10b981"
                                strokeWidth={2}
                                dot={false}
                                activeDot={{ r: 4, fill: "#10b981" }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
