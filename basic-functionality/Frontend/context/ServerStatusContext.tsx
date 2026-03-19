"use client";

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { API } from "@/lib/api";

interface ServerStatusContextType {
    isServerUp: boolean | null;
    isConfigured: boolean | null;
    isChecking: boolean;
    checkStatus: () => Promise<void>;
}

const ServerStatusContext = createContext<ServerStatusContextType | undefined>(undefined);

export function ServerStatusProvider({ children }: { children: ReactNode }) {
    const [isServerUp, setIsServerUp] = useState<boolean | null>(null);
    const [isConfigured, setIsConfigured] = useState<boolean | null>(null);
    const [isChecking, setIsChecking] = useState(false);

    const checkStatus = useCallback(async () => {
        setIsChecking(true);
        try {
            // Check setup status first
            const res = await fetch(`${API}/api/setup/status`, {
                signal: AbortSignal.timeout(3000)
            });
            if (res.ok) {
                const data = await res.json();
                setIsServerUp(true);
                setIsConfigured(data.is_configured);
            } else {
                setIsServerUp(false);
                setIsConfigured(null);
            }
        } catch (e) {
            setIsServerUp(false);
            setIsConfigured(null);
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
        <ServerStatusContext.Provider value={{ isServerUp, isConfigured, isChecking, checkStatus }}>
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
