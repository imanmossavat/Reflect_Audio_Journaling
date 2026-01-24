"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { API } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Settings, Shield, Cpu, Languages, FolderOpen, Save, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function SetupPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [systemInfo, setSystemInfo] = useState<any>(null);

    // Form state
    const [dataDir, setDataDir] = useState("");
    const [configDir, setConfigDir] = useState("");
    const [language, setLanguage] = useState("en");
    const [whisperModel, setWhisperModel] = useState("base");
    const [device, setDevice] = useState("cpu");

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await fetch(`${API}/api/setup/status`);
                const data = await res.json();

                if (data.is_configured && !window.location.search.includes("reconfigure=true")) {
                    router.push("/");
                    return;
                }

                setSystemInfo(data.system_info);
                setDataDir(data.current_config.data_dir);
                setConfigDir(data.current_config.config_dir);
                setLanguage(data.current_config.language || "en");
                setWhisperModel(data.current_config.whisper_model || "base");
                setDevice(data.system_info.suggested_device || "cpu");

                setLoading(false);
            } catch (error) {
                console.error("Failed to fetch setup status:", error);
                setLoading(false);
            }
        };

        fetchStatus();
    }, [router]);

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await fetch(`${API}/api/setup/run`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    data_dir: dataDir,
                    config_dir: configDir,
                    language,
                    whisper_model: whisperModel,
                    device
                })
            });

            const data = await res.json();
            if (res.ok) {
                toast.success(data.message || "Setup completed successfully!");
                // Small delay to let user see toast before redirect
                setTimeout(() => router.push("/"), 1500);
            } else {
                toast.error("Error: " + data.detail);
            }
        } catch (error) {
            console.error("Failed to save setup:", error);
            toast.error("Failed to save setup. Please check backend connection.");
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-zinc-50 dark:bg-zinc-950">
                <Loader2 className="w-8 h-8 text-zinc-400 animate-spin" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex flex-col items-center justify-center p-6 transition-colors duration-500">
            <div className="w-full max-w-2xl">
                <div className="flex flex-col items-center gap-4 mb-8 text-center">
                    <div className="w-16 h-16 rounded-2xl bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center border border-zinc-200 dark:border-zinc-800">
                        <Settings className="w-8 h-8 text-zinc-900 dark:text-zinc-100" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 mb-2">Welcome to REFLECT</h1>
                        <p className="text-zinc-500 dark:text-zinc-400">Let's set up your private audio journaling engine.</p>
                    </div>
                </div>

                <Card className="shadow-sm border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/50 backdrop-blur-sm">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-zinc-900 dark:text-zinc-100">
                            <Shield className="w-5 h-5 text-zinc-900 dark:text-zinc-100" />
                            Engine Configuration
                        </CardTitle>
                        <CardDescription>
                            Configure where your data is stored and how AI should behave.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Language */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-2">
                                    <Languages className="w-4 h-4" /> Language Preference
                                </label>
                                <Select value={language} onValueChange={setLanguage}>
                                    <SelectTrigger className="bg-white dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800">
                                        <SelectValue placeholder="Select Language" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="en">English (default)</SelectItem>
                                        <SelectItem value="nl">Dutch (Nederlands)</SelectItem>
                                    </SelectContent>
                                </Select>
                                <p className="text-[11px] text-zinc-500">Language for transcription & AI insights.</p>
                            </div>

                            {/* Device Selection */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-2">
                                    <Cpu className="w-4 h-4" /> Compute Device
                                </label>
                                <Select value={device} onValueChange={setDevice}>
                                    <SelectTrigger className="bg-white dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200">
                                        <SelectValue placeholder="Select Device" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="cpu">CPU (Standard)</SelectItem>
                                        {systemInfo?.cuda_available && <SelectItem value="cuda">NVIDIA GPU (CUDA)</SelectItem>}
                                        {systemInfo?.mps_available && <SelectItem value="mps">Apple Silicon (MPS)</SelectItem>}
                                        {!systemInfo?.cuda_available && <SelectItem value="cuda">Force CUDA Installation</SelectItem>}
                                    </SelectContent>
                                </Select>
                                <div className="flex gap-2 mt-1">
                                    {systemInfo?.cuda_available && <Badge variant="outline" className="text-[10px] bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20">CUDA Detected</Badge>}
                                    {systemInfo?.mps_available && <Badge variant="outline" className="text-[10px] bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/20">MPS Detected</Badge>}
                                </div>
                            </div>
                        </div>

                        {/* Whisper Model */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">AI Model Size (WhisperX)</label>
                            <Select value={whisperModel} onValueChange={setWhisperModel}>
                                <SelectTrigger className="bg-white dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800">
                                    <SelectValue placeholder="Select Model Size" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="tiny">Tiny (Fastest, least accurate)</SelectItem>
                                    <SelectItem value="base">Base (Fast, good for CPU)</SelectItem>
                                    <SelectItem value="small">Small (Balanced)</SelectItem>
                                    <SelectItem value="medium">Medium (Very Accurate, needs 4GB+ RAM)</SelectItem>
                                    <SelectItem value="large-v3">Large-v3 (Best, slow, needs 8GB+ VRAM)</SelectItem>
                                </SelectContent>
                            </Select>
                            <p className="text-[11px] text-zinc-500">Larger models are more accurate but much slower on CPU.</p>
                        </div>

                        <Separator className="bg-zinc-200 dark:bg-zinc-800" />

                        {/* Storage Paths */}
                        <div className="space-y-4">
                            <h3 className="text-sm font-medium text-zinc-900 dark:text-zinc-200 flex items-center gap-2">
                                <FolderOpen className="w-4 h-4" /> Storage Locations
                            </h3>

                            <div className="space-y-2">
                                <label className="text-xs text-zinc-500 dark:text-zinc-400">Data Directory (Audio & Transcripts)</label>
                                <Input
                                    value={dataDir}
                                    onChange={(e) => setDataDir(e.target.value)}
                                    placeholder="e.g. C:/Users/Me/Reflect/data"
                                    className="bg-white dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800"
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs text-zinc-500 dark:text-zinc-400">Configs Directory (Settings & Models)</label>
                                <Input
                                    value={configDir}
                                    onChange={(e) => setConfigDir(e.target.value)}
                                    placeholder="e.g. C:/Users/Me/Reflect/configs"
                                    className="bg-white dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800"
                                />
                            </div>
                        </div>

                    </CardContent>
                    <CardFooter className="bg-zinc-50 dark:bg-zinc-950/50 p-6 flex justify-end gap-4 border-t border-zinc-200 dark:border-zinc-800 rounded-b-lg">
                        <Button
                            className="bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 dark:text-zinc-900 text-white gap-2 transition-all"
                            onClick={handleSave}
                            disabled={saving}
                        >
                            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                            Finish Setup
                        </Button>
                    </CardFooter>
                </Card>

                <div className="mt-8 text-center">
                    <p className="text-xs text-zinc-500">
                        REFLECT stores all your data locally. No audio leaves your machine.
                    </p>
                </div>
            </div>
        </div>
    );
}
