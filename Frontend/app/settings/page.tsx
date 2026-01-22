"use client";

import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Save, RefreshCw, Trash2, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import ServerStatus from "@/components/ServerStatus";

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
            } catch (e) {}
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

    if (!settings && isServerUp) return <div className="p-10 text-xs font-medium text-zinc-500">Loading...</div>;

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
                        <section className="grid grid-cols-2 gap-4">
                            {["DATA_DIR", "CONFIG_DIR"].map((key) => (
                                <div key={key} className="space-y-2">
                                    <label className="text-[10px] font-bold uppercase text-zinc-500">{key.replace('_', ' ')}</label>
                                    <Input
                                        value={settings?.[key] || ""}
                                        onChange={(e) => updateField(key, e.target.value)}
                                        className="font-mono text-xs bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800"
                                    />
                                </div>
                            ))}
                        </section>

                        {/* ENGINE */}
                        <Card className="border-zinc-200 dark:border-zinc-800 shadow-none">
                            <CardHeader><CardTitle className="text-sm font-semibold">Engine Configuration</CardTitle></CardHeader>
                            <CardContent className="space-y-6">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-bold text-zinc-500 uppercase">Whisper Model</label>
                                        <Select value={settings?.WHISPER_MODEL} onValueChange={(v) => updateField('WHISPER_MODEL', v)}>
                                            <SelectTrigger className="text-sm"><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                {['tiny', 'base', 'small', 'medium', 'large', 'turbo'].map(m => (
                                                    <SelectItem key={m} value={m}>{m.toUpperCase()}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-bold text-zinc-500 uppercase">Device</label>
                                        <Select value={settings?.DEVICE} onValueChange={(v) => updateField('DEVICE', v)}>
                                            <SelectTrigger className="text-sm"><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="cpu">CPU</SelectItem>
                                                <SelectItem value="cuda">CUDA</SelectItem>
                                                <SelectItem value="mps">MPS</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-bold text-zinc-500 uppercase">Language</label>
                                    <Input className="w-24" value={settings?.LANGUAGE || ""} onChange={(e) => updateField('LANGUAGE', e.target.value)} />
                                </div>
                            </CardContent>
                        </Card>

                        {/* SEGMENTATION */}
                        <Card className="border-zinc-200 dark:border-zinc-800 shadow-none">
                            <CardHeader><CardTitle className="text-sm font-semibold">Segmentation</CardTitle></CardHeader>
                            <CardContent className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-bold text-zinc-500 uppercase">Percentile</label>
                                    <Input type="number" value={settings?.SEGMENTATION_PERCENTILE || 0} onChange={(e) => updateField('SEGMENTATION_PERCENTILE', parseInt(e.target.value))} />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-bold text-zinc-500 uppercase">Min Size</label>
                                    <Input type="number" value={settings?.SEGMENTATION_MIN_SIZE || 0} onChange={(e) => updateField('SEGMENTATION_MIN_SIZE', parseInt(e.target.value))} />
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* SIDEBAR */}
                    <div className="space-y-4">
                        <Card className="border-zinc-200 dark:border-zinc-800 shadow-sm">
                            <CardHeader><CardTitle className="text-[10px] font-bold uppercase text-zinc-500">Actions</CardTitle></CardHeader>
                            <CardContent className="space-y-2">
                                <Button className="w-full justify-start text-xs h-9" onClick={() => handleSave(false)} disabled={saving}>
                                    <Save className="h-3.5 w-3.5 mr-2" /> Save Changes
                                </Button>
                                <Button variant="outline" className="w-full justify-start text-xs h-9 border-amber-200 text-amber-700 hover:bg-amber-50" onClick={() => handleSave(true)} disabled={saving}>
                                    <RefreshCw className="h-3.5 w-3.5 mr-2" /> Save & Restart
                                </Button>
                                <Separator className="my-2" />
                                <Button variant="ghost" className="w-full justify-start text-xs h-9 text-zinc-400 hover:text-red-600" onClick={handleReset} disabled={saving}>
                                    <Trash2 className="h-3.5 w-3.5 mr-2" /> Reset to Defaults
                                </Button>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        </div>
    );
}