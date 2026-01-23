"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts";

interface PiiChartProps {
    data: { name: string; value: number }[];
}

export default function PiiChart({ data }: PiiChartProps) {
    if (!data || data.length === 0) return null;

    return (
        <Card className="col-span-4 md:col-span-2 border-zinc-200 dark:border-zinc-800 shadow-sm">
            <CardHeader>
                <CardTitle>Privacy Protection</CardTitle>
                <CardDescription>Redacted entities by type (e.g. PERSON, DATE)</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="h-[250px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data} layout="vertical">
                            <XAxis type="number" hide />
                            <YAxis
                                dataKey="name"
                                type="category"
                                stroke="#888888"
                                fontSize={10}
                                tickLine={false}
                                axisLine={false}
                                width={80}
                            />
                            <Tooltip
                                contentStyle={{ background: "#27272a", border: "none", color: "#fff", borderRadius: "8px", fontSize: "12px" }}
                                cursor={{ fill: "rgba(255,255,255,0.05)" }}
                            />
                            <Bar dataKey="value" fill="#ec4899" radius={[0, 4, 4, 0]} barSize={20} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
