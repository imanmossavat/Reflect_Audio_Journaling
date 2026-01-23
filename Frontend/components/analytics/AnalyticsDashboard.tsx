"use client";

import { useMemo } from "react";
import StatCards from "./StatCards";
import ActivityChart from "./ActivityChart";
import FillersChart from "./FillersChart";
import ConfidenceTrend from "./ConfidenceTrend";
import PiiChart from "./PiiChart";

interface AnalyticsDashboardProps {
    recordings: any[];
}

export default function AnalyticsDashboard({ recordings }: AnalyticsDashboardProps) {
    const stats = useMemo(() => {
        let totalRecordings = 0;
        let totalDurationSeconds = 0;
        let totalWords = 0;
        let totalConfidence = 0;
        let confidenceCount = 0;
        const fillerCounts: Record<string, number> = {};
        const dailyCounts: Record<string, number> = {};
        const piiCounts: Record<string, number> = {};
        const confidenceData: { id: string; confidence: number }[] = [];

        recordings.forEach(rec => {
            totalRecordings++;

            // Duration
            const dur = rec.duration;
            if (typeof dur === 'number') {
                totalDurationSeconds += dur;
            }

            // Confidence & Word Count
            const confStats = rec.speech?.confidence;
            if (confStats) {
                if (typeof confStats.mean === 'number') {
                    totalConfidence += confStats.mean;
                    confidenceCount++;
                    confidenceData.push({ id: rec.recording_id.slice(0, 6) + "...", confidence: Math.round(confStats.mean * 100) });
                }
                if (typeof confStats.count === 'number') {
                    totalWords += confStats.count;
                }
            }

            // Fillers
            const fillers = rec.speech?.fillers?.hits || [];
            fillers.forEach((hit: any) => {
                const phrase = hit.phrase?.toLowerCase() || "unknown";
                fillerCounts[phrase] = (fillerCounts[phrase] || 0) + 1;
            });

            // Activity
            if (rec.created_at) {
                const date = new Date(rec.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
                dailyCounts[date] = (dailyCounts[date] || 0) + 1;
            }

            // PII
            const piiSummary = rec.pii_summary || {};
            Object.entries(piiSummary).forEach(([label, count]) => {
                piiCounts[label] = (piiCounts[label] || 0) + (count as number);
            });
        });

        // Fillers Data for Chart
        const fillersChartData = Object.entries(fillerCounts)
            .map(([name, value]) => ({ name, value }))
            .sort((a, b) => b.value - a.value)
            .slice(0, 5);

        const mostUsedFiller = fillersChartData.length > 0 ? fillersChartData[0].name : "None";

        // Activity Data for Chart
        const activityChartData = Object.entries(dailyCounts)
            .map(([date, count]) => ({ date, count }))
            .reverse();

        const avgConfidence = confidenceCount > 0 ? totalConfidence / confidenceCount : 0;
        const totalHours = totalDurationSeconds / 3600;

        // PII Data for Chart
        const piiChartData = Object.entries(piiCounts)
            .map(([name, value]) => ({ name, value }))
            .sort((a, b) => b.value - a.value);

        return {
            totalRecordings,
            totalHours,
            totalWords,
            avgConfidence,
            mostUsedFiller,
            fillersChartData,
            activityChartData,
            confidenceData,
            piiChartData
        };
    }, [recordings]);

    return (
        <div className="space-y-6">
            <StatCards
                totalRecordings={stats.totalRecordings}
                totalHours={stats.totalHours}
                totalWords={stats.totalWords}
                avgConfidence={stats.avgConfidence}
                mostUsedFiller={stats.mostUsedFiller}
            />

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <ActivityChart data={stats.activityChartData} />
                <FillersChart data={stats.fillersChartData} />
                <ConfidenceTrend data={stats.confidenceData} />
                <PiiChart data={stats.piiChartData} />
            </div>
        </div>
    );
}
