"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useServerStatus } from "@/context/ServerStatusContext";

export function SetupGuard({ children }: { children: React.ReactNode }) {
    const { isConfigured, isServerUp } = useServerStatus();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        // If we are on the setup page, don't redirect away unless configured
        if (pathname === "/setup") {
            if (isConfigured === true && !window.location.search.includes("reconfigure=true")) {
                router.push("/");
            }
            return;
        }

        // If server is up but not configured, redirect to setup
        if (isServerUp && isConfigured === false) {
            router.push("/setup");
        }
    }, [isConfigured, isServerUp, pathname, router]);

    return <>{children}</>;
}
