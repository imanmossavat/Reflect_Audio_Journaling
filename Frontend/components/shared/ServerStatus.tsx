"use client";

import { useServerStatus } from "@/context/ServerStatusContext";
import { RefreshCw } from "lucide-react";

export default function ServerStatus() {
    const { isServerUp, isChecking, checkStatus } = useServerStatus();

    return (
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm">
            <div className={`h-2 w-2 rounded-full transition-all duration-500 ${isServerUp === true
                ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]'
                : isServerUp === false
                    ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'
                    : 'bg-amber-500 animate-pulse'
                }`} />
            <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 min-w-[80px]">
                {isServerUp === true ? 'Engine Online' : isServerUp === false ? 'Engine Offline' : 'Connecting...'}
            </span>

            {isServerUp === false && (
                <button
                    onClick={checkStatus}
                    disabled={isChecking}
                    className="ml-1 p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-full transition-colors"
                >
                    <RefreshCw className={`h-3 w-3 text-zinc-400 ${isChecking ? 'animate-spin' : ''}`} />
                </button>
            )}
        </div>
    );
}
