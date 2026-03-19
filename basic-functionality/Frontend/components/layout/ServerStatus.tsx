"use client";

import { useEffect, useState, useCallback } from "react";
import { API } from "@/lib/api";

export default function ServerStatus() {
    const [isServerUp, setIsServerUp] = useState<boolean | null>(null);

    const checkStatus = useCallback(async () => {
        try {
            const res = await fetch(`${API}/api/recordings`, {
                signal: AbortSignal.timeout(3000)
            });
            setIsServerUp(res.ok);
        } catch (error) {
            setIsServerUp(false);
        }
    }, []);

    useEffect(() => {
        checkStatus();
        const interval = setInterval(checkStatus, 5000);
        return () => clearInterval(interval);
    }, [checkStatus]);

    return (
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm transition-all">
            <div className={`h-2 w-2 rounded-full transition-all duration-500 ${
                isServerUp === true
                    ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]'
                    : isServerUp === false
                        ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'
                        : 'bg-amber-500 animate-pulse'
            }`} />
            <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">
        {isServerUp === true ? 'Engine Online' : isServerUp === false ? 'Engine Offline' : 'Connecting...'}
      </span>
        </div>
    );
}