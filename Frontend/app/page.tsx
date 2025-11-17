"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="min-h-screen w-full bg-zinc-50 dark:bg-black font-sans">
      <div className="mx-auto max-w-3xl py-24 px-6">

        {/* HEADER */}
        <header className="mb-12">
          <h1 className="text-4xl font-bold tracking-tight text-black dark:text-zinc-50">
            REFLECT
          </h1>
          <p className="mt-2 text-lg text-zinc-600 dark:text-zinc-400">
            Your private AI-powered audio journal.
          </p>
        </header>

        {/* ACTION CARDS */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">

          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle>New Recording</CardTitle>
              <CardDescription>
                Upload or record a new journal entry.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/upload">
                <Button className="w-full">Upload Audio</Button>
              </Link>
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle>Your Library</CardTitle>
              <CardDescription>
                Browse all your recordings and transcripts.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/recordings">
                <Button variant="secondary" className="w-full">
                  View Library
                </Button>
              </Link>
            </CardContent>
          </Card>
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle>Settings</CardTitle>
              <CardDescription>
                Configure language, models and segmentation.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/settings">
                <Button variant="outline" className="w-full">
                  Open Settings
                </Button>
              </Link>
            </CardContent>
          </Card>

        </div>

        {/* FOOTER */}
        <footer className="mt-24 text-center text-sm text-zinc-500 dark:text-zinc-600">
          Built for privacy. All data stays on your device.
        </footer>
      </div>
    </div>
  );
}
