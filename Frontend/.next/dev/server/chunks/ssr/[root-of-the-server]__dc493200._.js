module.exports = [
"[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[project]/lib/api.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "API",
    ()=>API,
    "Api",
    ()=>Api
]);
const API = "http://127.0.0.1:8000";
const Api = {
    // Recordings
    listRecordings: async ()=>{
        const res = await fetch(`${API}/api/recordings`, {
            cache: "no-store"
        });
        if (!res.ok) throw new Error("Failed to fetch recordings");
        return res.json();
    },
    getRecording: async (id)=>{
        const res = await fetch(`${API}/api/recordings/${id}`, {
            cache: "no-store"
        });
        if (res.status === 404) return {}; // Handle not found gracefully in UI
        if (!res.ok) throw new Error("Failed to fetch recording");
        return res.json();
    },
    updateRecordingMeta: async (id, payload)=>{
        const res = await fetch(`${API}/api/recordings/${id}/meta`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error("Failed to update metadata");
        return res.json();
    },
    deleteRecording: async (id)=>{
        const res = await fetch(`${API}/api/recordings/${id}`, {
            method: "DELETE"
        });
        if (!res.ok) throw new Error("Failed to delete recording");
        return res.json();
    },
    deleteAudio: async (id)=>{
        const res = await fetch(`${API}/api/recordings/${id}/audio`, {
            method: "DELETE"
        });
        if (!res.ok) throw new Error("Failed to delete audio");
        return res.json();
    },
    deleteTranscripts: async (id)=>{
        const res = await fetch(`${API}/api/recordings/${id}/transcript?version=all`, {
            method: "DELETE"
        });
        if (!res.ok) throw new Error("Failed to delete transcripts");
        return res.json();
    },
    deleteSegments: async (id)=>{
        const res = await fetch(`${API}/api/recordings/${id}/segments`, {
            method: "DELETE"
        });
        if (!res.ok) throw new Error("Failed to delete segments");
        return res.json();
    },
    // Audio & Uploads
    uploadAudio: async (formData)=>{
        const res = await fetch(`${API}/api/recordings/upload`, {
            method: "POST",
            body: formData
        });
        if (!res.ok) {
            const err = await res.json().catch(()=>({}));
            throw new Error(err?.detail || "Upload failed");
        }
        return res.json();
    },
    createTextEntry: async (text)=>{
        const res = await fetch(`${API}/api/recordings/text`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text
            })
        });
        if (!res.ok) {
            const err = await res.json().catch(()=>({}));
            throw new Error(err?.detail || "Failed to create text entry");
        }
        return res.json();
    },
    // Transcripts & Processing
    getTranscript: async (id, version = "original")=>{
        const res = await fetch(`${API}/api/recordings/${id}/transcript?version=${version}`);
        if (!res.ok) return {
            text: ""
        };
        return res.json(); // returns { text: "..." }
    },
    saveEditedTranscript: async (id, text)=>{
        const res = await fetch(`${API}/api/recordings/${id}/transcript/edited`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text
            })
        });
        if (!res.ok) throw new Error("Failed to save transcript");
        return res.json();
    },
    finalizeRecording: async (id, editedTranscript)=>{
        const formData = new FormData();
        formData.append("recording_id", id);
        formData.append("edited_transcript", editedTranscript);
        const res = await fetch(`${API}/api/recordings/finalize`, {
            method: "POST",
            body: formData
        });
        if (!res.ok) throw new Error("Processing failed");
        return res.json();
    },
    syncPii: async (id, findings)=>{
        const res = await fetch(`${API}/api/recordings/${id}/pii`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                findings
            })
        });
        if (!res.ok) throw new Error("Failed to sync PII");
        return res.json();
    },
    // Settings
    getSettings: async ()=>{
        const res = await fetch(`${API}/api/settings`);
        if (!res.ok) throw new Error("Failed to fetch settings");
        return res.json();
    },
    updateSettings: async (settings, restart = false)=>{
        const payload = {
            ...settings,
            RESTART_REQUIRED: restart
        };
        const res = await fetch(`${API}/api/settings/update`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error("Failed to update settings");
        return res.json();
    },
    resetSettings: async ()=>{
        const res = await fetch(`${API}/api/settings/reset`, {
            method: "POST"
        });
        if (!res.ok) throw new Error("Failed to reset settings");
        return res.json();
    },
    openFolder: async (path)=>{
        const res = await fetch(`${API}/api/settings/open-folder`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                path
            })
        });
        if (!res.ok) throw new Error("Failed to open folder");
        return res.json();
    },
    // AI Tools
    semanticSearch: async (query)=>{
        const res = await fetch(`${API}/api/search/semantic`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                query
            })
        });
        if (!res.ok) return [];
        const data = await res.json();
        return data.hits || [];
    }
};
}),
"[project]/context/ServerStatusContext.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ServerStatusProvider",
    ()=>ServerStatusProvider,
    "useServerStatus",
    ()=>useServerStatus
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/api.ts [app-ssr] (ecmascript)");
"use client";
;
;
;
const ServerStatusContext = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["createContext"])(undefined);
function ServerStatusProvider({ children }) {
    const [isServerUp, setIsServerUp] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    const [isConfigured, setIsConfigured] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(null);
    const [isChecking, setIsChecking] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(false);
    const checkStatus = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useCallback"])(async ()=>{
        setIsChecking(true);
        try {
            // Check setup status first
            const res = await fetch(`${__TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["API"]}/api/setup/status`, {
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
        } finally{
            setIsChecking(false);
        }
    }, []);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        checkStatus();
        const interval = setInterval(checkStatus, 10000); // Check every 10s
        return ()=>clearInterval(interval);
    }, [
        checkStatus
    ]);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(ServerStatusContext.Provider, {
        value: {
            isServerUp,
            isConfigured,
            isChecking,
            checkStatus
        },
        children: children
    }, void 0, false, {
        fileName: "[project]/context/ServerStatusContext.tsx",
        lineNumber: 50,
        columnNumber: 9
    }, this);
}
function useServerStatus() {
    const context = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useContext"])(ServerStatusContext);
    if (context === undefined) {
        throw new Error("useServerStatus must be used within a ServerStatusProvider");
    }
    return context;
}
}),
"[externals]/next/dist/server/app-render/action-async-storage.external.js [external] (next/dist/server/app-render/action-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/action-async-storage.external.js", () => require("next/dist/server/app-render/action-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-unit-async-storage.external.js [external] (next/dist/server/app-render/work-unit-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-unit-async-storage.external.js", () => require("next/dist/server/app-render/work-unit-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-async-storage.external.js [external] (next/dist/server/app-render/work-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-async-storage.external.js", () => require("next/dist/server/app-render/work-async-storage.external.js"));

module.exports = mod;
}),
"[project]/components/shared/SetupGuard.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "SetupGuard",
    ()=>SetupGuard
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/navigation.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$context$2f$ServerStatusContext$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/context/ServerStatusContext.tsx [app-ssr] (ecmascript)");
"use client";
;
;
;
;
function SetupGuard({ children }) {
    const { isConfigured, isServerUp } = (0, __TURBOPACK__imported__module__$5b$project$5d2f$context$2f$ServerStatusContext$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useServerStatus"])();
    const router = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useRouter"])();
    const pathname = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["usePathname"])();
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
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
    }, [
        isConfigured,
        isServerUp,
        pathname,
        router
    ]);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["Fragment"], {
        children: children
    }, void 0, false);
}
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__dc493200._.js.map