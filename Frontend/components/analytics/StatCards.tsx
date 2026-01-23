"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Mic, Clock, Zap, Activity } from "lucide-react";

interface StatCardsProps {
    totalRecordings: number;
    totalHours: number;
    totalWords: number;
    avgConfidence: number;
    mostUsedFiller: string;
}

export default function StatCards({
    totalRecordings,
    totalHours,
    totalWords,
    avgConfidence,
    mostUsedFiller
}: StatCardsProps) {
    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <Card className="border-zinc-200 dark:border-zinc-800 shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Total Recordings</CardTitle>
                    <Mic className="h-4 w-4 text-zinc-500" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{totalRecordings}</div>
                    <p className="text-xs text-zinc-500">Lifetime entries</p>
                </CardContent>
            </Card>

            <Card className="border-zinc-200 dark:border-zinc-800 shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Total Duration</CardTitle>
                    <Clock className="h-4 w-4 text-zinc-500" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{totalHours.toFixed(1)}h</div>
                    <p className="text-xs text-zinc-500">Of recorded audio</p>
                </CardContent>
            </Card>

            <Card className="border-zinc-200 dark:border-zinc-800 shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Total Words</CardTitle>
                    <Activity className="h-4 w-4 text-zinc-500" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{totalWords.toLocaleString()}</div>
                    <p className="text-xs text-zinc-500">Transcribed words</p>
                </CardContent>
            </Card>

            <Card className="border-zinc-200 dark:border-zinc-800 shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Avg Confidence</CardTitle>
                    <Activity className="h-4 w-4 text-zinc-500" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{(avgConfidence * 100).toFixed(0)}%</div>
                    <p className="text-xs text-zinc-500">Model certainty</p>
                </CardContent>
            </Card>

            <Card className="border-zinc-200 dark:border-zinc-800 shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Top Filler</CardTitle>
                    <Zap className="h-4 w-4 text-amber-500" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold capitalize">{mostUsedFiller || "—"}</div>
                    <p className="text-xs text-zinc-500">Most frequent hesitation</p>
                </CardContent>
            </Card>
        </div>
    );
}
