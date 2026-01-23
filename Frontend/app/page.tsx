"use client";

import { useEffect, useState, useCallback } from "react";
import { API } from "@/lib/api";
import { Separator } from "@/components/ui/separator";

import HeroHeader from "@/components/dashboard/HeroHeader";
import ActionGrid from "@/components/dashboard/ActionGrid";
import SidebarCards from "@/components/dashboard/SidebarCards";
import LibraryCard from "@/components/dashboard/LibraryCard";
import FeatureFooter from "@/components/dashboard/FeatureFooter";

export default function Home() {
  const [totalCount, setTotalCount] = useState<number | null>(null);

  // Still fetch recordings count, but don't manage server status here
  useEffect(() => {
    const fetchCount = async () => {
      try {
        const res = await fetch(`${API}/api/recordings`);
        if (res.ok) {
          const data = await res.json();
          const count = Array.isArray(data) ? data.length : (data.recordings?.length || 0);
          setTotalCount(count);
        }
      } catch (e) {
        setTotalCount(null);
      }
    };
    fetchCount();
  }, []);

  return (
    <div className="min-h-screen w-full bg-zinc-50 dark:bg-zinc-950 transition-colors duration-500 overflow-x-hidden">
      <div className="mx-auto max-w-[1400px] px-6 py-10 space-y-6">

        <div className="max-w-5xl mx-auto">
          <HeroHeader />
        </div>

        <Separator className="bg-zinc-200 dark:bg-zinc-800 max-w-5xl mx-auto" />

        <div className="grid grid-cols-1 lg:grid-cols-13 gap-6 items-stretch">
          <div className="lg:col-span-6">
            <ActionGrid />
          </div>

          <div className="lg:col-span-4">
            <LibraryCard totalCount={totalCount} />
          </div>

          <div className="lg:col-span-3">
            <SidebarCards />
          </div>
        </div>

        <div className="max-w-5xl mx-auto">
          <FeatureFooter />
        </div>
      </div>
    </div>
  );
}