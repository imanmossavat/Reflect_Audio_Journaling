export function formatDateTime(iso?: string) {
    if (!iso) return "Unknown";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso; // fallback if something weird comes in
    return new Intl.DateTimeFormat("nl-NL", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(d);
}
