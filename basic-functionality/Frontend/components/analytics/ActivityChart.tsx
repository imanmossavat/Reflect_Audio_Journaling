"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts";

interface ActivityChartProps {
    data: { date: string; count: number }[];
}

export default function ActivityChart({ data }: ActivityChartProps) {
    if (!data || data.length === 0) return null;

    return (
        <Card className="col-span-4 border-zinc-200 dark:border-zinc-800 shadow-sm">
            <CardHeader>
                <CardTitle>Activity</CardTitle>
                <CardDescription>Recordings over the last 30 days</CardDescription>
            </CardHeader>
            <CardContent className="pl-2">
                <div className="h-[200px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data}>
                            <XAxis
                                dataKey="date"
                                stroke="#888888"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                            />
                            <YAxis
                                stroke="#888888"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                                tickFormatter={(value) => `${value}`}
                            />
                            <Tooltip
                                contentStyle={{ background: "#333", border: "none", color: "#fff", borderRadius: "8px", fontSize: "12px" }}
                                cursor={{ fill: "transparent" }}
                            />
                            <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
