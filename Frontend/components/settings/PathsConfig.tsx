"use client";

import { Input } from "@/components/ui/input";

interface PathsConfigProps {
    dataDir?: string;
    configDir?: string;
    onChange: (key: string, value: string) => void;
}

export default function PathsConfig({ dataDir, configDir, onChange }: PathsConfigProps) {
    return (
        <section className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase text-zinc-500">DATA DIR</label>
                <Input
                    value={dataDir || ""}
                    onChange={(e) => onChange('DATA_DIR', e.target.value)}
                    className="font-mono text-xs bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800"
                />
            </div>
            <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase text-zinc-500">CONFIG DIR</label>
                <Input
                    value={configDir || ""}
                    onChange={(e) => onChange('CONFIG_DIR', e.target.value)}
                    className="font-mono text-xs bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800"
                />
            </div>
        </section>
    );
}
