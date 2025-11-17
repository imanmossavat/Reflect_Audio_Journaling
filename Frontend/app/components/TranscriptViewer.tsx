"use client";

export default function TranscriptViewer({ text, pii = [] }) {
  return (
    <div className="whitespace-pre-wrap leading-7 text-zinc-800 dark:text-zinc-200 mt-6">
      {text}
    </div>
  );
}
