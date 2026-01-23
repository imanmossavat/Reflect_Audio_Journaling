import { ShieldCheck, Cpu, FileLock2 } from "lucide-react";

export default function FeatureFooter() {
    return (
        <footer className="pt-10 flex flex-col items-center gap-4">
            <div className="flex items-center gap-6">
                <div className="flex items-center gap-1.5 text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                    <ShieldCheck className="h-3 w-3" /> On-Device
                </div>
                <div className="flex items-center gap-1.5 text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                    <Cpu className="h-3 w-3" /> No Cloud
                </div>
                <div className="flex items-center gap-1.5 text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                    <FileLock2 className="h-3 w-3" /> Private Storage
                </div>
            </div>
            <p className="text-[11px] text-zinc-400 dark:text-zinc-600">
                Reflect v1.0.0 — Your thoughts stay on your hardware.
            </p>
        </footer>
    );
}
