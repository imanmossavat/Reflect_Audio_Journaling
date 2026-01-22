"use client";

import * as React from "react";

export default function BadgePill({ text }: { text: string }) {
    return (
        <span className="text-xs px-2 py-1 rounded border border-zinc-200 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/40">
      {text}
    </span>
    );
}
