"use client";

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { API } from "@/lib/api";

interface ServerStatusContextType {
    isServerUp: boolean | null;
    isChecking: boolean;
    checkStatus: () => Promise<void>;
}

const ServerStatusContext = createContext<ServerStatusContextType | undefined>(undefined);

export function ServerStatusProvider({ children }: { children: ReactNode }) {
    const [isServerUp, setIsServerUp] = useState<boolean | null>(null);
    const [isChecking, setIsChecking] = useState(false);

    // We use a lightweight check. Since /api/settings exists, let's try that.
    // Or fallback to /api/recordings if we want to be sure DB is also reachable.
    // /api/settings is safer as it shouldn't be heavy.
    const checkStatus = useCallback(async () => {
        setIsChecking(true);
        try {
            // Short timeout to fail fast
            const res = await fetch(`${API}/api/settings`, {
                signal: AbortSignal.timeout(3000)
            });
            if (res.ok) {
                setIsServerUp(true);
            } else {
                setIsServerUp(false);
            }
        } catch (e) {
            setIsServerUp(false);
        } finally {
            setIsChecking(false);
        }
    }, []);

    useEffect(() => {
        checkStatus();
        const interval = setInterval(checkStatus, 10000); // Check every 10s
        return () => clearInterval(interval);
    }, [checkStatus]);

    return (
        <ServerStatusContext.Provider value={{ isServerUp, isChecking, checkStatus }}>
            {children}
        </ServerStatusContext.Provider>
    );
}

export function useServerStatus() {
    const context = useContext(ServerStatusContext);
    if (context === undefined) {
        throw new Error("useServerStatus must be used within a ServerStatusProvider");
    }
    return context;
}
