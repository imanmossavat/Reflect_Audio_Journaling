"use client";

import Link from "next/link";
import { Settings2, LayoutDashboard, LibraryBig } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import RecentRecordings from "@/components/recording/RecentRecordings";

interface SidebarCardsProps {
    totalCount: number | null;
}

export default function SidebarCards({ totalCount }: SidebarCardsProps) {
    return (
        <div className="space-y-6">
            <Card className="shadow-sm border-zinc-200 dark:border-zinc-800">
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                    <div>
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <LibraryBig className="h-4 w-4 text-zinc-500" /> Library
                        </CardTitle>
                        <div className="text-[10px] uppercase tracking-wider text-zinc-400 font-bold mt-1">
                            {totalCount === null ? "..." : `${totalCount} entries`}
                        </div>
                    </div>
                    <Link href="/recordings">
                        <Button variant="ghost" size="sm" className="h-7 text-[10px] font-bold uppercase hover:bg-zinc-100">View all</Button>
                    </Link>
                </CardHeader>
                <CardContent>
                    <RecentRecordings />
                </CardContent>
            </Card>

            <Card className="shadow-sm border-zinc-200 dark:border-zinc-800">
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        <LayoutDashboard className="h-4 w-4 text-zinc-500" /> Insights
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <Link href="/analytics">
                        <Button variant="outline" className="w-full h-10 text-xs font-semibold border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-900">
                            Explore Insights
                        </Button>
                    </Link>
                </CardContent>
            </Card>

            <Card className="shadow-sm border-zinc-200 dark:border-zinc-800">
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        <Settings2 className="h-4 w-4 text-zinc-500" /> Settings
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <Link href="/settings">
                        <Button variant="outline" className="w-full h-10 text-xs font-semibold border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-900">
                            Engine Preferences
                        </Button>
                    </Link>
                </CardContent>
            </Card>
        </div>
    );
}
