"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Api } from "@/lib/api";

import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";

import { MoreHorizontal, Trash2, FileText, Waves, AudioLines } from "lucide-react";
import { toast } from "sonner";

type ActionKey = "audio" | "transcripts" | "segments" | "all";

export default function RecordingActions({ id }: { id: string }) {
    const router = useRouter();
    const [open, setOpen] = React.useState(false);
    const [pending, setPending] = React.useState<ActionKey | null>(null);

    const actions: Record<ActionKey, { label: string; url: string; redirectTo?: string; danger?: boolean; icon: any }> = {
        audio: {
            label: "Delete audio",
            url: `/api/recordings/${id}/audio`,
            icon: AudioLines,
        },
        transcripts: {
            label: "Delete transcripts",
            url: `/api/recordings/${id}/transcript?version=all`,
            icon: FileText,
        },
        segments: {
            label: "Delete segments",
            url: `/api/recordings/${id}/segments`,
            icon: Waves,
        },
        all: {
            label: "Delete recording (everything)",
            url: `/api/recordings/${id}`,
            redirectTo: "/recordings",
            danger: true,
            icon: Trash2,
        },
    };

    async function runDelete(key: ActionKey) {
        const promise = (async () => {
            if (key === "all") {
                await Api.deleteRecording(id);
            } else if (key === "audio") {
                await Api.deleteAudio(id);
            } else if (key === "transcripts") {
                await Api.deleteTranscripts(id);
            } else if (key === "segments") {
                await Api.deleteSegments(id);
            }
        })();

        toast.promise(promise, {
            loading: "Deleting...",
            success: () => {
                if (actions[key].redirectTo) router.push(actions[key].redirectTo!);
                else router.refresh();
                return "Deleted successfully";
            },
            error: "Delete failed"
        });
    }

    const title = pending ? actions[pending].label : "Confirm";
    const isDanger = pending ? !!actions[pending].danger : false;

    return (
        <>
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="icon" className="h-9 w-9">
                        <MoreHorizontal className="h-4 w-4" />
                    </Button>
                </DropdownMenuTrigger>

                <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                    <DropdownMenuSeparator />

                    {(["audio", "transcripts", "segments"] as ActionKey[]).map((k) => {
                        const Icon = actions[k].icon;
                        return (
                            <DropdownMenuItem
                                key={k}
                                onSelect={(e) => {
                                    e.preventDefault();
                                    setPending(k);
                                    setOpen(true);
                                }}
                            >
                                <Icon className="mr-2 h-4 w-4" />
                                {actions[k].label}
                            </DropdownMenuItem>
                        );
                    })}

                    <DropdownMenuSeparator />

                    <DropdownMenuItem
                        className="text-red-600 focus:text-red-600"
                        onSelect={(e) => {
                            e.preventDefault();
                            setPending("all");
                            setOpen(true);
                        }}
                    >
                        <Trash2 className="mr-2 h-4 w-4" />
                        {actions.all.label}
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>

            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>{title}</AlertDialogTitle>
                        <AlertDialogDescription>
                            This cannot be undone. If you’re deleting the whole recording, it will remove audio, transcripts, segments, and metadata.
                        </AlertDialogDescription>
                    </AlertDialogHeader>

                    <AlertDialogFooter>
                        <AlertDialogCancel
                            onClick={() => {
                                setPending(null);
                                setOpen(false);
                            }}
                        >
                            Cancel
                        </AlertDialogCancel>

                        <AlertDialogAction
                            className={isDanger ? "bg-red-600 hover:bg-red-700" : undefined}
                            onClick={async () => {
                                if (!pending) return;
                                const key = pending;
                                setPending(null);
                                setOpen(false);
                                await runDelete(key);
                            }}
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
}