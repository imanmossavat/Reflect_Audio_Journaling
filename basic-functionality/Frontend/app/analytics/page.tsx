"use client";

import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import AnalyticsDashboard from "@/components/analytics/AnalyticsDashboard";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import PageHeader from "@/components/shared/PageHeader";
import { PageLoader } from "@/components/shared/LoadingSpinner";

export default function AnalyticsPage() {
    const [recordings, setRecordings] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API}/api/recordings`);
            if (!res.ok) throw new Error("Failed to fetch data");
            const data = await res.json();
            const list = Array.isArray(data) ? data : (data.recordings || []);
            setRecordings(list);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    if (loading) return <PageLoader />;

    if (error) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-zinc-50 dark:bg-zinc-950 gap-4">
                <p className="text-red-500 font-medium">Error loading analytics</p>
                <Button onClick={fetchData} variant="outline" size="sm" className="gap-2">
                    <RefreshCw className="h-4 w-4" /> Retry
                </Button>
            </div>
        );
    }

    return (
        <div className="min-h-screen w-full bg-zinc-50 dark:bg-zinc-950">
            <div className="mx-auto max-w-6xl px-6 py-10">
                <PageHeader
                    title="Analytics"
                    description="Insights from your verbal journal."
                />

                <AnalyticsDashboard recordings={recordings} />
            </div>
        </div>
    );
}
