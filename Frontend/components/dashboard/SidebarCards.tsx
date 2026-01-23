"use client";

import Link from "next/link";
import { Settings2, LayoutDashboard } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function SidebarCards() {
    return (
        <div className="flex flex-col h-full space-y-4">
            <Card className="shadow-sm border-zinc-200 dark:border-zinc-800 flex flex-col">
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        <LayoutDashboard className="h-4 w-4 text-zinc-500" /> Insights
                    </CardTitle>
                    <CardDescription className="text-[11px] leading-relaxed">
                        Analyze your emotional triggers, topic clusters, and journaling frequency over time.
                    </CardDescription>
                </CardHeader>
                <CardContent className="mt-auto">
                    <Link href="/analytics">
                        <Button variant="outline" className="w-full h-10 text-xs font-semibold border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-900">
                            Explore Metrics
                        </Button>
                    </Link>
                </CardContent>
            </Card>

            <Card className="shadow-sm border-zinc-200 dark:border-zinc-800 mt-auto flex flex-col">
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        <Settings2 className="h-4 w-4 text-zinc-500" /> Settings
                    </CardTitle>
                    <CardDescription className="text-[11px] leading-relaxed">
                        Manage your local model settings, recording quality, and private export options.
                    </CardDescription>
                </CardHeader>
                <CardContent className="mt-auto">
                    <Link href="/settings">
                        <Button variant="outline" className="w-full h-10 text-xs font-semibold border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-900">
                            System Preferences
                        </Button>
                    </Link>
                </CardContent>
            </Card>
        </div>
    );
}
