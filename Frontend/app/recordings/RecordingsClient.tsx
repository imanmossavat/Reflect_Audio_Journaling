"use client";

import * as React from "react";
import Link from "next/link";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";

type Recording = any;

function formatDateTime(iso?: string) {
    if (!iso) return "Unknown date";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "Unknown date";
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).format(d);
}

function formatDateOnly(d?: Date) {
    if (!d) return "Pick a date";
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(d);
}

function extractSearchableText(rec: Recording): string {
    const chunks: string[] = [];

    const safePush = (v: unknown) => {
        if (typeof v === "string" && v.trim()) chunks.push(v.trim());
    };

    // basics
    safePush(rec?.title);
    safePush(rec?.recording_id);

    // tags
    if (Array.isArray(rec?.tags)) {
        for (const tag of rec.tags) safePush(tag);
    }

    // backend-provided search text (the real reason we're here)
    safePush(rec?.search_text);

    // fallback (if you ever decide to embed transcripts directly)
    const t = rec?.transcripts ?? rec?.transcript ?? {};
    if (typeof t === "string") safePush(t);
    safePush(t?.text);

    return chunks.join("\n").toLowerCase();
}

type StatusFilter = "all" | "original" | "edited" | "redacted";
type AudioFilter = "all" | "audio" | "no_audio";
type SortMode = "newest" | "oldest" | "title";

export default function RecordingsClient({ items }: { items: Recording[] }) {
    const [query, setQuery] = React.useState("");
    const [status, setStatus] = React.useState<StatusFilter>("all");
    const [audio, setAudio] = React.useState<AudioFilter>("all");
    const [sort, setSort] = React.useState<SortMode>("newest");
    const [from, setFrom] = React.useState<Date | undefined>(undefined);
    const [to, setTo] = React.useState<Date | undefined>(undefined);
    const [selectedTags, setSelectedTags] = React.useState<string[]>([]);

    const allTags = React.useMemo(() => {
        const set = new Set<string>();
        for (const r of items ?? []) {
            if (Array.isArray(r?.tags)) {
                for (const t of r.tags) {
                    if (typeof t === "string" && t.trim()) set.add(t.trim());
                }
            }
        }
        return Array.from(set).sort((a, b) => a.localeCompare(b));
    }, [items]);

    const indexed = React.useMemo(() => {
        return (items ?? []).map((rec) => {
            const t = rec?.transcripts || {};
            const hasEdited = !!t?.edited;
            const hasRedacted = !!t?.redacted;
            const hasOriginal = !!t?.original;
            const hasAudio = rec?.has_audio ?? !!rec?.audio;

            const created = rec?.created_at ? new Date(rec.created_at) : null;
            const createdTime = created && !Number.isNaN(created.getTime()) ? created.getTime() : 0;

            return {
                rec,
                hasEdited,
                hasRedacted,
                hasOriginal,
                hasAudio,
                created,
                createdTime,
                searchable: extractSearchableText(rec),
            };
        });
    }, [items]);

    const filtered = React.useMemo(() => {
        const q = query.trim().toLowerCase();

        const inRange = (d: Date | null) => {
            if (!d) return true;
            const time = d.getTime();

            if (from) {
                const f = new Date(from);
                f.setHours(0, 0, 0, 0);
                if (time < f.getTime()) return false;
            }
            if (to) {
                const t = new Date(to);
                t.setHours(23, 59, 59, 999);
                if (time > t.getTime()) return false;
            }
            return true;
        };

        const passStatus = (x: (typeof indexed)[number]) => {
            if (status === "all") return true;
            if (status === "edited") return x.hasEdited;
            if (status === "redacted") return x.hasRedacted;
            // original = has original and NOT edited/redacted (your call; this is the clean definition)
            return x.hasOriginal && !x.hasEdited && !x.hasRedacted;
        };

        const passAudio = (x: (typeof indexed)[number]) => {
            if (audio === "all") return true;
            if (audio === "audio") return x.hasAudio;
            return !x.hasAudio;
        };

        const passTags = (rec: Recording) => {
            if (selectedTags.length === 0) return true;
            const recTags: string[] = Array.isArray(rec?.tags) ? rec.tags : [];
            // AND behaviour: must contain all selected tags
            return selectedTags.every((t) => recTags.includes(t));
        };

        let out = indexed.filter((x) => {
            if (q && !x.searchable.includes(q)) return false;
            if (!inRange(x.created)) return false;
            if (!passStatus(x)) return false;
            if (!passAudio(x)) return false;
            if (!passTags(x.rec)) return false;
            return true;
        });

        out.sort((a, b) => {
            if (sort === "newest") return b.createdTime - a.createdTime;
            if (sort === "oldest") return a.createdTime - b.createdTime;

            const at = (a.rec?.title || a.rec?.recording_id || "").toString().toLowerCase();
            const bt = (b.rec?.title || b.rec?.recording_id || "").toString().toLowerCase();
            return at.localeCompare(bt);
        });

        return out;
    }, [indexed, query, from, to, status, audio, sort, selectedTags]);

    const activeFilterCount =
        (query.trim() ? 1 : 0) +
        (status !== "all" ? 1 : 0) +
        (audio !== "all" ? 1 : 0) +
        (sort !== "newest" ? 1 : 0) +
        (from ? 1 : 0) +
        (to ? 1 : 0) +
        (selectedTags.length ? 1 : 0);

    const clearAll = () => {
        setQuery("");
        setStatus("all");
        setAudio("all");
        setSort("newest");
        setFrom(undefined);
        setTo(undefined);
        setSelectedTags([]);
    };

    return (
        <div className="space-y-4">
            <Card className="p-4">
                <div className="flex flex-col gap-3">
                    {/* Search row */}
                    <div className="flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
                        <div className="flex-1">
                            <Input
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Search title + tags + transcript text…"
                                className="h-10"
                            />
                        </div>

                        <div className="flex gap-2 items-center justify-start md:justify-end">
                            {activeFilterCount > 0 && (
                                <Button variant="secondary" onClick={clearAll} className="h-10">
                                    Clear filters
                                </Button>
                            )}
                            <Badge variant="secondary" className="h-6">
                                {filtered.length} / {items?.length ?? 0}
                            </Badge>
                        </div>
                    </div>

                    <Separator />

                    {/* Filters grid */}
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
                        {/* Date range */}
                        <div className="md:col-span-5 flex gap-2">
                            <Popover>
                                <PopoverTrigger asChild>
                                    <Button variant="outline" className="h-10 flex-1 justify-start">
                                        <span className="text-zinc-500 mr-2">From:</span>
                                        <span className={cn(!from && "text-zinc-400")}>{formatDateOnly(from)}</span>
                                    </Button>
                                </PopoverTrigger>
                                <PopoverContent className="p-0 w-auto" align="start">
                                    <Calendar mode="single" selected={from} onSelect={setFrom} initialFocus />
                                    <div className="p-2">
                                        <Button
                                            variant="ghost"
                                            className="w-full"
                                            onClick={() => setFrom(undefined)}
                                            disabled={!from}
                                        >
                                            Clear
                                        </Button>
                                    </div>
                                </PopoverContent>
                            </Popover>

                            <Popover>
                                <PopoverTrigger asChild>
                                    <Button variant="outline" className="h-10 flex-1 justify-start">
                                        <span className="text-zinc-500 mr-2">To:</span>
                                        <span className={cn(!to && "text-zinc-400")}>{formatDateOnly(to)}</span>
                                    </Button>
                                </PopoverTrigger>
                                <PopoverContent className="p-0 w-auto" align="start">
                                    <Calendar mode="single" selected={to} onSelect={setTo} initialFocus />
                                    <div className="p-2">
                                        <Button
                                            variant="ghost"
                                            className="w-full"
                                            onClick={() => setTo(undefined)}
                                            disabled={!to}
                                        >
                                            Clear
                                        </Button>
                                    </div>
                                </PopoverContent>
                            </Popover>
                        </div>

                        {/* Status */}
                        <div className="md:col-span-2">
                            <Select value={status} onValueChange={(v) => setStatus(v as StatusFilter)}>
                                <SelectTrigger className="h-10 w-full">
                                    <SelectValue placeholder="Status" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All statuses</SelectItem>
                                    <SelectItem value="original">Original</SelectItem>
                                    <SelectItem value="edited">Edited</SelectItem>
                                    <SelectItem value="redacted">Redacted</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Audio */}
                        <div className="md:col-span-2">
                            <Select value={audio} onValueChange={(v) => setAudio(v as AudioFilter)}>
                                <SelectTrigger className="h-10 w-full">
                                    <SelectValue placeholder="Audio" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Audio: all</SelectItem>
                                    <SelectItem value="audio">Has audio</SelectItem>
                                    <SelectItem value="no_audio">No audio</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Sort */}
                        <div className="md:col-span-3">
                            <Select value={sort} onValueChange={(v) => setSort(v as SortMode)}>
                                <SelectTrigger className="h-10 w-full">
                                    <SelectValue placeholder="Sort" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="newest">Sort: newest</SelectItem>
                                    <SelectItem value="oldest">Sort: oldest</SelectItem>
                                    <SelectItem value="title">Sort: title</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Tags */}
                        <div className="md:col-span-12 lg:col-span-12 space-y-2">
                            <Popover>
                                <PopoverTrigger asChild>
                                    <Button
                                        variant="outline"
                                        className="h-10 w-full justify-between"
                                    >
        <span className="text-sm text-zinc-600">
          {selectedTags.length > 0 ? "Filter by tags" : "Add tag filter"}
        </span>
                                        {selectedTags.length > 0 && (
                                            <Badge variant="secondary">{selectedTags.length}</Badge>
                                        )}
                                    </Button>
                                </PopoverTrigger>

                                <PopoverContent className="w-72 p-3" align="start">
                                    <div className="space-y-2">
                                        <div className="text-xs font-medium text-zinc-500">Tags</div>

                                        {allTags.length === 0 && (
                                            <div className="text-sm text-zinc-500 py-2">
                                                No tags yet
                                            </div>
                                        )}

                                        <div className="flex flex-wrap gap-1">
                                            {allTags.map((tag) => {
                                                const active = selectedTags.includes(tag);

                                                return (
                                                    <button
                                                        key={tag}
                                                        type="button"
                                                        onClick={() => {
                                                            setSelectedTags((prev) =>
                                                                active
                                                                    ? prev.filter((t) => t !== tag)
                                                                    : [...prev, tag]
                                                            );
                                                        }}
                                                        className={[
                                                            "px-2 py-1 rounded-full text-xs border transition",
                                                            active
                                                                ? "bg-zinc-900 text-white border-zinc-900 dark:bg-zinc-100 dark:text-zinc-900 dark:border-zinc-100"
                                                                : "border-zinc-300 text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900",
                                                        ].join(" ")}
                                                    >
                                                        {tag}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </PopoverContent>
                            </Popover>

                            {/* Selected tags (clean, no duplication) */}
                            {selectedTags.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                    {selectedTags.map((t) => (
                                        <Badge
                                            key={t}
                                            variant="secondary"
                                            className="cursor-pointer"
                                            onClick={() =>
                                                setSelectedTags((prev) => prev.filter((x) => x !== t))
                                            }
                                        >
                                            {t}
                                        </Badge>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {activeFilterCount > 0 && (
                        <div className="flex flex-wrap gap-2 pt-1">
                            {query.trim() && <Badge>Query</Badge>}
                            {from && <Badge variant="secondary">From</Badge>}
                            {to && <Badge variant="secondary">To</Badge>}
                            {status !== "all" && <Badge variant="secondary">Status</Badge>}
                            {audio !== "all" && <Badge variant="secondary">Audio</Badge>}
                            {sort !== "newest" && <Badge variant="secondary">Sort</Badge>}
                            {selectedTags.length > 0 && <Badge variant="secondary">Tags</Badge>}
                        </div>
                    )}
                </div>
            </Card>

            {/* List */}
            <div className="space-y-3">
                {filtered.map(({ rec, hasAudio, hasEdited, hasRedacted }) => {
                    const title = rec?.title || rec?.recording_id;
                    const created = formatDateTime(rec?.created_at);

                    return (
                        <Link key={rec.recording_id} href={`/recordings/${rec.recording_id}`} className="block">
                            <Card className="p-4 hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors">
                                <div className="flex items-start justify-between gap-4">
                                    <div className="min-w-0 flex-1">
                                        <div className="font-semibold truncate">{title}</div>
                                        <div className="text-sm text-zinc-500">{created}</div>

                                        {Array.isArray(rec?.tags) && rec.tags.length > 0 && (
                                            <div className="mt-2 flex flex-wrap gap-1">
                                                {rec.tags.map((tag: string) => (
                                                    <Badge
                                                        key={tag}
                                                        variant="outline"
                                                        className="text-xs cursor-pointer"
                                                        onClick={(e) => {
                                                            e.preventDefault();
                                                            setSelectedTags([tag]);
                                                        }}
                                                    >
                                                        {tag}
                                                    </Badge>
                                                ))}
                                            </div>
                                        )}
                                    </div>

                                    <div className="flex gap-2 flex-wrap justify-end">
                                        {hasAudio ? <Badge>audio</Badge> : <Badge variant="secondary">no audio</Badge>}
                                        {hasEdited && <Badge variant="secondary">edited</Badge>}
                                        {hasRedacted && <Badge variant="secondary">redacted</Badge>}
                                        {!hasEdited && !hasRedacted && <Badge variant="secondary">original</Badge>}
                                    </div>
                                </div>
                            </Card>
                        </Link>
                    );
                })}

                {filtered.length === 0 && (
                    <Card className="p-8 text-center text-sm text-zinc-600">No results.</Card>
                )}
            </div>
        </div>
    );
}