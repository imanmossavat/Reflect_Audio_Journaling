"use client";

import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SettingsPage() {
  const [settings, setSettings] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/settings`)
      .then(res => res.json())
      .then(data => setSettings(data.settings));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    await fetch(`${API}/api/settings/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    setSaving(false);
  };

  if (!settings) return <div className="p-10">Loading...</div>;

  return (
    <div className="min-h-screen p-10 max-w-2xl mx-auto space-y-6">
      <h1 className="text-3xl font-bold">Settings</h1>

      <div className="space-y-4">
        <label className="block">
          <div className="text-sm font-medium mb-1">Language</div>
          <Input
            value={settings.LANGUAGE}
            onChange={(e) =>
              setSettings({ ...settings, LANGUAGE: e.target.value })
            }
          />
        </label>

        <label className="block">
          <div className="text-sm font-medium mb-1">Whisper Model</div>
          <Input
            value={settings.WHISPER_MODEL}
            onChange={(e) =>
              setSettings({ ...settings, WHISPER_MODEL: e.target.value })
            }
          />
        </label>

        <label className="block">
          <div className="text-sm font-medium mb-1">Segmentation Method</div>
          <Input
            value={settings.SEGMENTATION_METHOD}
            onChange={(e) =>
              setSettings({ ...settings, SEGMENTATION_METHOD: e.target.value })
            }
          />
        </label>
      </div>

      <Button className="w-full" onClick={handleSave}>
        {saving ? "Saving…" : "Save Settings"}
      </Button>
    </div>
  );
}
