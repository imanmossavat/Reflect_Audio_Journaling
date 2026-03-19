export function normalizeTagsFromString(s: string): string[] {
    const raw = s
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean);

    const seen = new Set<string>();
    const out: string[] = [];

    for (const t of raw) {
        const key = t.toLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        out.push(t);
    }

    return out;
}

export function fmtPct01(n?: number) {
    if (typeof n !== "number" || !Number.isFinite(n)) return "–";
    return `${(n * 100).toFixed(1)}%`;
}

export function fmtNum(n?: number, digits = 3) {
    if (typeof n !== "number" || !Number.isFinite(n)) return "–";
    return n.toFixed(digits);
}

export function fmtSeconds(n?: number) {
    if (typeof n !== "number" || !Number.isFinite(n)) return "–";
    return `${n.toFixed(2)}s`;
}
