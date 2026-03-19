"use client";

import Link from "next/link";
import { LibraryBig } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import RecentRecordings from "@/components/recording/RecentRecordings";

interface LibraryCardProps {
    totalCount: number | null;
}

export default function LibraryCard({ totalCount }: LibraryCardProps) {
    return (
        <Card className="shadow-sm border-zinc-200 dark:border-zinc-800 flex flex-col h-full">
            <CardHeader className="pb-0">
                <CardTitle className="text-lg flex items-center gap-2">
                    <LibraryBig className="h-4 w-4 text-zinc-500" /> Library
                </CardTitle>
                <CardDescription className="text-xs mt-1">Your recent captures and notes.</CardDescription>
                <div className="text-[10px] font-bold text-zinc-400 mt-2 uppercase tracking-tighter">
                    {totalCount === null ? (
                        <span className="animate-pulse">Syncing...</span>
                    ) : (
                        `${totalCount} total ${totalCount === 1 ? 'entry' : 'entries'}`
                    )}
                </div>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col pt-6">
                <div className="flex-1">
                    <RecentRecordings />
                </div>

                <Link href="/recordings" className="block mt-6">
                    <Button variant="outline" className="w-full h-10 text-xs font-semibold border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-900">
                        See All Recordings
                    </Button>
                </Link>
            </CardContent>
        </Card>
    );
}
