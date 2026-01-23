"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

interface BadgePillProps {
  text: string;
  variant?: "default" | "secondary" | "destructive" | "outline";
}

export default function BadgePill({ text, variant = "default" }: BadgePillProps) {
  const variants = {
    default: "border-zinc-200 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/40",
    secondary: "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900 dark:bg-blue-900/20 dark:text-blue-300",
    destructive: "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-300",
    outline: "border-zinc-300 bg-transparent"
  };

  return (
    <span className={cn(
      "text-xs px-2 py-1 rounded border",
      variants[variant] || variants.default
    )}>
      {text}
    </span>
  );
}
