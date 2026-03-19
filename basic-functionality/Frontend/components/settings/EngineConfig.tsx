"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";

interface EngineConfigProps {
    whisperModel?: string;
    device?: string;
    language?: string;
    onChange: (key: string, value: string) => void;
}

export default function EngineConfig({ whisperModel, device, language, onChange }: EngineConfigProps) {
    return (
        <Card className="border-zinc-200 dark:border-zinc-800 shadow-none">
            <CardHeader><CardTitle className="text-sm font-semibold">Engine Configuration</CardTitle></CardHeader>
            <CardContent className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-zinc-500 uppercase">Whisper Model</label>
                        <Select value={whisperModel} onValueChange={(v) => onChange('WHISPER_MODEL', v)}>
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
                        <Select value={device} onValueChange={(v) => onChange('DEVICE', v)}>
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
                    <Input className="w-24" value={language || ""} onChange={(e) => onChange('LANGUAGE', e.target.value)} />
                </div>
            </CardContent>
        </Card>
    );
}
