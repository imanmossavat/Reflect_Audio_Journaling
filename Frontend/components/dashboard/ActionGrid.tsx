"use client";

import Link from "next/link";
import { Upload, Mic, PencilLine, ArrowRight, Sparkles } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";

export default function ActionGrid() {
    return (
        <Card className="shadow-sm border-zinc-200 dark:border-zinc-800 h-full flex flex-col">
            <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-amber-500" />
                    New entry
                </CardTitle>
                <CardDescription className="text-xs">Start a session or import existing audio.</CardDescription>
            </CardHeader>

            <CardContent className="flex-1 flex flex-col justify-between">
                <div className="space-y-3">
                    <Link href="/upload?tab=upload" className="group block">
                        <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 group-hover:border-zinc-400 dark:group-hover:border-zinc-600 group-hover:shadow-md transition-all p-4">
                            <Upload className="h-5 w-5 mb-2 text-zinc-400 group-hover:text-zinc-900 dark:group-hover:text-zinc-100 transition-colors" />
                            <div className="text-sm font-bold flex items-center justify-between">
                                Upload <ArrowRight className="h-3 w-3 opacity-0 -translate-x-2 group-hover:translate-x-0 group-hover:opacity-100 transition-all" />
                            </div>
                            <div className="mt-1 text-xs text-zinc-500 leading-normal">Analyze existing files.</div>
                        </div>
                    </Link>

                    <Link href="/upload?tab=record" className="group block">
                        <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 group-hover:border-red-400 dark:group-hover:border-red-900/50 group-hover:shadow-md transition-all p-4">
                            <Mic className="h-5 w-5 mb-2 text-red-500 group-hover:scale-110 transition-transform" />
                            <div className="text-sm font-bold flex items-center justify-between">
                                Record <ArrowRight className="h-3 w-3 opacity-0 -translate-x-2 group-hover:translate-x-0 group-hover:opacity-100 transition-all" />
                            </div>
                            <div className="mt-1 text-xs text-zinc-500 leading-normal">Capture live audio.</div>
                        </div>
                    </Link>

                    <Link href="/upload?tab=write" className="group block">
                        <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 group-hover:border-zinc-400 dark:group-hover:border-zinc-600 group-hover:shadow-md transition-all p-4">
                            <PencilLine className="h-5 w-5 mb-2 text-zinc-400 group-hover:text-zinc-900 dark:group-hover:text-zinc-100 transition-colors" />
                            <div className="text-sm font-bold flex items-center justify-between">
                                Write <ArrowRight className="h-3 w-3 opacity-0 -translate-x-2 group-hover:translate-x-0 group-hover:opacity-100 transition-all" />
                            </div>
                            <div className="mt-1 text-xs text-zinc-500 leading-normal">Direct text entry.</div>
                        </div>
                    </Link>
                </div>
            </CardContent>
        </Card>
    );
}
