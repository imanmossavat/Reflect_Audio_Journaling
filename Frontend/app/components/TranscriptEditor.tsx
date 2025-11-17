"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export default function TranscriptEditor({ defaultValue, onSave }: any) {
  const [value, setValue] = useState(defaultValue);

  return (
    <div className="space-y-4">
      <Textarea
        className="w-full h-96"
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />

      <Button onClick={() => onSave(value)}>Opslaan</Button>
    </div>
  );
}
