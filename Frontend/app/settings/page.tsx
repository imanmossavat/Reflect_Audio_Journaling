"use client";

import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import { CheckCircle2, RefreshCw } from "lucide-react";
import Link from "next/link";
import ServerStatus from "@/components/layout/ServerStatus";

import EngineConfig from "@/components/settings/EngineConfig";
import SegmentationConfig from "@/components/settings/SegmentationConfig";
import PathsConfig from "@/components/settings/PathsConfig";
import SettingsActions from "@/components/settings/SettingsActions";

export default function SettingsPage() {
    const [settings, setSettings] = useState<any>(null);
    const [saving, setSaving] = useState(false);
    const [isServerUp, setIsServerUp] = useState(true);
    const [showToast, setShowToast] = useState(false);

    useEffect(() => {
        fetch(`${API}/api/settings`)
            .then(res => res.json())
            .then(data => setSettings(data.settings))
            .catch(() => setIsServerUp(false));
    }, []);

    useEffect(() => {
        if (isServerUp) return;
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`${API}/api/settings`);
                if (res.ok) {
                    const data = await res.json();
                    setSettings(data.settings);
                    setIsServerUp(true);
                }
            } catch (e) { }
        }, 2000);
        return () => clearInterval(interval);
    }, [isServerUp]);

    const handleSave = async (forceRestart: boolean) => {
        setSaving(true);
        try {
            const res = await fetch(`${API}/api/settings/update`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ...settings, RESTART_REQUIRED: forceRestart }),
            });
            if (res.ok && forceRestart) {
                setIsServerUp(false);
            } else if (res.ok) {
                setShowToast(true);
                setTimeout(() => setShowToast(false), 3000);
            }
        } finally {
            setSaving(false);
        }
    };

    const handleReset = async () => {
        if (!confirm("Reset all settings to default?")) return;
        setSaving(true);
        try {
            await fetch(`${API}/api/settings/reset`, { method: "POST" });
            setIsServerUp(false);
        } finally {
            setSaving(false);
        }
    };

    const updateField = (key: string, value: any) => {
        setSettings({ ...settings, [key]: value });
    };

    if (!settings && isServerUp) return <div className="p-6 text-xs font-medium text-zinc-500">Loading settings...</div>;

    return (
        <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
            {/* Simple Toast */}
            {showToast && (
                <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 px-4 py-2 rounded-md shadow-lg text-sm transition-all">
                    <CheckCircle2 className="h-4 w-4" /> Settings Saved
                </div>
            )}

            {/* Clean Reboot Overlay */}
            {!isServerUp && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 dark:bg-zinc-950/80 backdrop-blur-sm">
                    <div className="flex flex-col items-center gap-3">
                        <RefreshCw className="h-6 w-6 animate-spin text-zinc-500" />
                        <p className="text-sm font-medium">Restarting Engine...</p>
                    </div>
                </div>
            )}

            <div className="max-w-5xl mx-auto px-6 py-12">
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <Link href="/" className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 mb-2 block">
                            ← Back
                        </Link>
                        <h1 className="text-3xl font-bold">Settings</h1>
                    </div>
                    <ServerStatus />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-8">
                        {/* PATHS */}
                        <PathsConfig
                            dataDir={settings?.DATA_DIR}
                            configDir={settings?.CONFIG_DIR}
                            onChange={updateField}
                        />

                        {/* ENGINE */}
                        <EngineConfig
                            whisperModel={settings?.WHISPER_MODEL}
                            device={settings?.DEVICE}
                            language={settings?.LANGUAGE}
                            onChange={updateField}
                        />

                        {/* SEGMENTATION */}
                        <SegmentationConfig
                            percentile={settings?.SEGMENTATION_PERCENTILE}
                            minSize={settings?.SEGMENTATION_MIN_SIZE}
                            onChange={updateField}
                        />
                    </div>

                    {/* SIDEBAR */}
                    <div className="space-y-4">
                        <SettingsActions saving={saving} onSave={handleSave} onReset={handleReset} />
                    </div>
                </div>
            </div>
        </div>
    );
}

