"use client";

import { Volume2, VolumeX } from "lucide-react";

export default function AudioPlayer({
  src,
  hasAudio,
}: {
  src: string;
  hasAudio: boolean;
}) {
  if (!hasAudio) {
    return (
      <div className="flex items-center gap-3 rounded-md border border-dashed border-zinc-200 dark:border-zinc-800 p-4 text-sm text-zinc-500">
        <VolumeX className="h-4 w-4 shrink-0" />
        <span>This entry has no audio.</span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs text-zinc-500">
        <Volume2 className="h-4 w-4" />
        <span>Audio recording</span>
      </div>

      <audio controls className="w-full rounded">
        <source src={src} />
        Your browser does not support audio.
      </audio>
    </div>
  );
}
