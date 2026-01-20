"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Mic,
  Upload,
  PencilLine,
  LibraryBig,
  Settings2,
  ShieldCheck,
  Cpu,
  FileLock2,
  ArrowRight,
} from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen w-full bg-zinc-50 dark:bg-zinc-950">
      <div className="mx-auto max-w-5xl px-6 py-14 md:py-20 space-y-10">
        {/* HERO */}
        <header className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-center">
              <ShieldCheck className="h-5 w-5 text-zinc-900 dark:text-zinc-100" />
            </div>
            <div className="flex items-center gap-2">
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-zinc-950 dark:text-zinc-50">
                REFLECT
              </h1>
              <Badge variant="secondary" className="hidden sm:inline-flex">
                local-first
              </Badge>
            </div>
          </div>

          <p className="text-lg md:text-xl text-zinc-600 dark:text-zinc-400 max-w-2xl">
            A private journal that turns voice or text into transcripts, segments, and insights.
            Everything stays local. Because the internet does not deserve your thoughts.
          </p>

          {/* trust strip */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
            <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/40 px-4 py-3 flex items-center gap-3">
              <FileLock2 className="h-4 w-4 text-zinc-700 dark:text-zinc-300" />
              <div className="text-sm text-zinc-700 dark:text-zinc-300">
                Local storage (no cloud)
              </div>
            </div>
            <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/40 px-4 py-3 flex items-center gap-3">
              <Cpu className="h-4 w-4 text-zinc-700 dark:text-zinc-300" />
              <div className="text-sm text-zinc-700 dark:text-zinc-300">
                Runs on your machine
              </div>
            </div>
            <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/40 px-4 py-3 flex items-center gap-3">
              <ShieldCheck className="h-4 w-4 text-zinc-700 dark:text-zinc-300" />
              <div className="text-sm text-zinc-700 dark:text-zinc-300">
                PII detection + redaction
              </div>
            </div>
          </div>
        </header>

        <Separator className="bg-zinc-200 dark:bg-zinc-800" />

        {/* MAIN ACTIONS */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* New Entry (big) */}
          <Card className="shadow-sm lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-xl">New entry</CardTitle>
              <CardDescription>
                Start however you want. You can always edit and re-run processing later.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <Link href="/upload" className="block">
                  <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:bg-zinc-50 dark:hover:bg-zinc-900/70 transition p-4 h-full">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Upload className="h-4 w-4" />
                        Upload audio
                      </div>
                      <ArrowRight className="h-4 w-4 text-zinc-400" />
                    </div>
                    <div className="mt-2 text-xs text-zinc-500">
                      Import a file and generate transcript + redaction.
                    </div>
                  </div>
                </Link>

                <Link href="/upload" className="block">
                  <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:bg-zinc-50 dark:hover:bg-zinc-900/70 transition p-4 h-full">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Mic className="h-4 w-4" />
                        Record
                      </div>
                      <ArrowRight className="h-4 w-4 text-zinc-400" />
                    </div>
                    <div className="mt-2 text-xs text-zinc-500">
                      Record inside the app. No external tools.
                    </div>
                  </div>
                </Link>

                <Link href="/upload" className="block">
                  <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:bg-zinc-50 dark:hover:bg-zinc-900/70 transition p-4 h-full">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <PencilLine className="h-4 w-4" />
                        Write text
                      </div>
                      <ArrowRight className="h-4 w-4 text-zinc-400" />
                    </div>
                    <div className="mt-2 text-xs text-zinc-500">
                      Type an entry and optionally run PII + segmentation.
                    </div>
                  </div>
                </Link>
              </div>

              <div className="flex flex-col sm:flex-row gap-2">
                <Link href="/upload" className="w-full sm:w-auto">
                  <Button className="w-full sm:w-auto">Start a new entry</Button>
                </Link>
                <Link href="/recordings" className="w-full sm:w-auto">
                  <Button variant="secondary" className="w-full sm:w-auto">
                    Go to library
                  </Button>
                </Link>
              </div>

              <div className="text-xs text-zinc-500">
                Tip: “Finalize processing” updates segments + PII after edits.
              </div>
            </CardContent>
          </Card>

          {/* Right column */}
          <div className="space-y-6">
            <Card className="shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <LibraryBig className="h-4 w-4" />
                  Library
                </CardTitle>
                <CardDescription>
                  Browse recordings, search transcripts, manage tags.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Link href="/recordings">
                  <Button variant="secondary" className="w-full">
                    View library
                  </Button>
                </Link>
              </CardContent>
            </Card>

            <Card className="shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Settings2 className="h-4 w-4" />
                  Settings
                </CardTitle>
                <CardDescription>
                  Configure language, models, and processing options.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Link href="/settings">
                  <Button variant="outline" className="w-full">
                    Open settings
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* FOOTER */}
        <footer className="pt-6 text-center text-sm text-zinc-500 dark:text-zinc-600">
          Built for privacy. Your data stays on your device.
        </footer>
      </div>
    </div>
  );
}
