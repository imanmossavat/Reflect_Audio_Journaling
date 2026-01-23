import { Loader2 } from "lucide-react";

export function LoadingSpinner({ className }: { className?: string }) {
    return (
        <Loader2 className={`animate-spin text-zinc-400 ${className}`} />
    );
}

export function PageLoader() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-950">
            <LoadingSpinner className="h-8 w-8" />
        </div>
    );
}
