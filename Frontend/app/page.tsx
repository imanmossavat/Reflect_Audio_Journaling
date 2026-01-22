"use client";

import Link from "next/link";
import { useEffect, useState, useCallback } from "react";
import { API } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Mic, Upload, PencilLine, LibraryBig, Settings2,
  ShieldCheck, Cpu, FileLock2, ArrowRight, Activity, Sparkles, RefreshCw
} from "lucide-react";
import RecentRecordings from "@/components/RecentRecordings";

export default function Home() {
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [isServerUp, setIsServerUp] = useState<boolean | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const checkStatus = useCallback(async () => {
    setIsRefreshing(true);
    try {
      // Modern way to handle timeouts in 2026
      const res = await fetch(`${API}/api/recordings`, {
        signal: AbortSignal.timeout(3000)
      });

      if (res.ok) {
        const data = await res.json();
        const count = Array.isArray(data) ? data.length : (data.recordings?.length || 0);
        setTotalCount(count);
        setIsServerUp(true);
      } else {
        setIsServerUp(false);
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.warn("Connection timed out.");
      } else {
        console.error("Connection failed:", error);
      }

      setIsServerUp(false);
      setTotalCount(null);
    } finally {
      setIsRefreshing(false);
    }
  }, []);
  useEffect(() => {
    // Initial check
    checkStatus();

    // Polling interval: Check every 5 seconds
    const interval = setInterval(checkStatus, 5000);

    return () => clearInterval(interval);
  }, [checkStatus]);

  return (
      <div className="min-h-screen w-full bg-zinc-50 dark:bg-zinc-950 transition-colors duration-500">
        <div className="mx-auto max-w-5xl px-6 py-14 md:py-20 space-y-10">

          {/* HERO */}
          <header className="space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">

              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-center shadow-sm">
                  <ShieldCheck className="h-7 w-7 text-zinc-900 dark:text-zinc-100" />
                </div>
                <div className="flex flex-col">
                  <h1 className="text-4xl font-bold tracking-tight text-zinc-950 dark:text-zinc-50 leading-none">
                    REFLECT
                  </h1>
                  <span className="text-[10px] font-bold text-zinc-400 tracking-[0.2em] mt-1.5 uppercase">Local Intelligence</span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {/* Status Indicator */}
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm">
                  <div className={`h-2 w-2 rounded-full transition-all duration-500 ${
                      isServerUp === true
                          ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]'
                          : isServerUp === false
                              ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'
                              : 'bg-amber-500 animate-pulse'
                  }`} />
                  <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 min-w-[80px]">
                  {isServerUp === true ? 'Engine Online' : isServerUp === false ? 'Engine Offline' : 'Connecting...'}
                </span>

                  {/* Manual Retry Button - only shows when offline */}
                  {isServerUp === false && (
                      <button
                          onClick={checkStatus}
                          disabled={isRefreshing}
                          className="ml-1 p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-full transition-colors"
                      >
                        <RefreshCw className={`h-3 w-3 text-zinc-400 ${isRefreshing ? 'animate-spin' : ''}`} />
                      </button>
                  )}
                </div>

                <Badge variant="outline" className="hidden sm:flex h-7 border-zinc-300 dark:border-zinc-700 text-zinc-500">
                  v1.0.0
                </Badge>
              </div>
            </div>

            <p className="text-lg text-zinc-600 dark:text-zinc-400 max-w-2xl leading-relaxed">
              Your private, local-first intelligence hub. Capture audio or text and generate redacted, searchable insights without cloud processing.
            </p>
          </header>

          <Separator className="bg-zinc-200 dark:bg-zinc-800" />

          {/* MAIN ACTIONS */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">

            <Card className="shadow-sm lg:col-span-2 flex flex-col border-zinc-200 dark:border-zinc-800">
              <CardHeader>
                <CardTitle className="text-xl flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-amber-500" />
                  New entry
                </CardTitle>
                <CardDescription>Start a session or import existing audio.</CardDescription>
              </CardHeader>

              <CardContent className="flex-1 flex flex-col justify-between space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <Link href="/upload?tab=upload" className="group">
                    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 group-hover:border-zinc-400 dark:group-hover:border-zinc-600 group-hover:shadow-md transition-all p-5 h-full">
                      <Upload className="h-5 w-5 mb-3 text-zinc-400 group-hover:text-zinc-900 dark:group-hover:text-zinc-100 transition-colors" />
                      <div className="text-sm font-bold flex items-center justify-between">
                        Upload <ArrowRight className="h-3 w-3 opacity-0 -translate-x-2 group-hover:translate-x-0 group-hover:opacity-100 transition-all" />
                      </div>
                      <div className="mt-1 text-xs text-zinc-500 leading-normal">Analyze existing files.</div>
                    </div>
                  </Link>

                  <Link href="/upload?tab=record" className="group">
                    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 group-hover:border-red-400 dark:group-hover:border-red-900/50 group-hover:shadow-md transition-all p-5 h-full">
                      <Mic className="h-5 w-5 mb-3 text-red-500 group-hover:scale-110 transition-transform" />
                      <div className="text-sm font-bold flex items-center justify-between">
                        Record <ArrowRight className="h-3 w-3 opacity-0 -translate-x-2 group-hover:translate-x-0 group-hover:opacity-100 transition-all" />
                      </div>
                      <div className="mt-1 text-xs text-zinc-500 leading-normal">Capture live audio.</div>
                    </div>
                  </Link>

                  <Link href="/upload?tab=write" className="group">
                    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 group-hover:border-zinc-400 dark:group-hover:border-zinc-600 group-hover:shadow-md transition-all p-5 h-full">
                      <PencilLine className="h-5 w-5 mb-3 text-zinc-400 group-hover:text-zinc-900 dark:group-hover:text-zinc-100 transition-colors" />
                      <div className="text-sm font-bold flex items-center justify-between">
                        Write <ArrowRight className="h-3 w-3 opacity-0 -translate-x-2 group-hover:translate-x-0 group-hover:opacity-100 transition-all" />
                      </div>
                      <div className="mt-1 text-xs text-zinc-500 leading-normal">Direct text entry.</div>
                    </div>
                  </Link>
                </div>

                <div className="bg-zinc-100 dark:bg-zinc-900/50 border border-zinc-200/50 dark:border-zinc-800/50 p-4 rounded-xl flex items-start gap-3 mt-auto">
                  <div className="p-1.5 rounded-lg bg-white dark:bg-zinc-800 shadow-sm">
                    <Activity className="h-3.5 w-3.5 text-zinc-500" />
                  </div>
                  <div className="text-[11px] text-zinc-500 leading-relaxed italic">
                    <strong>Privacy First:</strong> Your transcripts and PII data never leave this machine.
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="space-y-6">
              <Card className="shadow-sm border-zinc-200 dark:border-zinc-800 flex flex-col">
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <LibraryBig className="h-4 w-4 text-zinc-500" /> Library
                    </CardTitle>
                    <div className="text-[10px] font-bold text-zinc-400 mt-1 uppercase tracking-tighter">
                      {totalCount === null ? (
                          <span className="animate-pulse">Syncing...</span>
                      ) : (
                          `${totalCount} total ${totalCount === 1 ? 'entry' : 'entries'}`
                      )}
                    </div>
                  </div>
                  <Link href="/recordings">
                    <Button variant="ghost" size="sm" className="h-8 text-xs font-semibold hover:bg-zinc-200 dark:hover:bg-zinc-800">
                      See all
                    </Button>
                  </Link>
                </CardHeader>
                <CardContent className="flex-1">
                  <RecentRecordings />
                </CardContent>
              </Card>

              <Card className="shadow-sm border-zinc-200 dark:border-zinc-800">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Settings2 className="h-4 w-4 text-zinc-500" /> Settings
                  </CardTitle>
                  <CardDescription className="text-xs">System configuration.</CardDescription>
                </CardHeader>
                <CardContent>
                  <Link href="/settings">
                    <Button variant="outline" className="w-full h-10 text-xs font-medium border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-900">
                      Engine Preferences
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            </div>
          </div>

          <footer className="pt-10 flex flex-col items-center gap-4">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-1.5 text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                <ShieldCheck className="h-3 w-3" /> On-Device
              </div>
              <div className="flex items-center gap-1.5 text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                <Cpu className="h-3 w-3" /> No Cloud
              </div>
              <div className="flex items-center gap-1.5 text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                <FileLock2 className="h-3 w-3" /> Private Storage
              </div>
            </div>
            <p className="text-[11px] text-zinc-400 dark:text-zinc-600">
              Reflect v1.0.0 — Your thoughts stay on your hardware.
            </p>
          </footer>
        </div>
      </div>
  );
}