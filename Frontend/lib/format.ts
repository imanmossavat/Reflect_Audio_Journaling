export function formatDateTime(iso?: string) {
    if (!iso) return "Unknown";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso; // Return raw ISO string if date is invalid
    return new Intl.DateTimeFormat("nl-NL", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(d);
}
