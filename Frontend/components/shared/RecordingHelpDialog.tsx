import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { HelpCircle, Trash2, Edit3, Shield, Layers, BarChart3, ScanFace } from "lucide-react";
import { Button } from "@/components/ui/button";

export function RecordingHelpDialog() {
    return (
        <Dialog>
            <DialogTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2 text-zinc-500">
                    <HelpCircle className="h-4 w-4" />
                    <span className="hidden md:inline">Page Guide</span>
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Recording Viewer Guide</DialogTitle>
                    <DialogDescription>
                        Understanding your data and analysis.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-8 pt-4">

                    {/* Segments */}
                    <div className="flex items-start gap-4">
                        <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg shrink-0">
                            <Layers className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                            <h4 className="font-semibold text-sm mb-1">Segments</h4>
                            <p className="text-sm text-zinc-500">
                                The AI breaks your recording into logical <strong>Segments</strong> based on topic changes or pauses.
                                These are used for semantic search, helping you find specific moments without searching the whole text.
                            </p>
                        </div>
                    </div>

                    {/* Insights / Confidence */}
                    <div className="flex items-start gap-4">
                        <div className="p-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg shrink-0">
                            <BarChart3 className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                        </div>
                        <div>
                            <h4 className="font-semibold text-sm mb-1">Confidence Score</h4>
                            <p className="text-sm text-zinc-500">
                                Under the <strong>Insights</strong> tab, the "Confidence" score shows how certain the AI was about the transcription accuracy for each word.
                                <br />Lower scores (red/orange) might indicate mumbling, background noise, or distinct names that might need manual correction.
                            </p>
                        </div>
                    </div>

                    {/* PII / Redaction */}
                    <div className="flex items-start gap-4">
                        <div className="p-2 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg shrink-0">
                            <Shield className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                        </div>
                        <div>
                            <h4 className="font-semibold text-sm mb-1">Privacy & Redaction</h4>
                            <p className="text-sm text-zinc-500">
                                Personal info (Names, Locations) is automatically detected and highlighted.
                                Click highlighted words in the transcript to <strong>Redact</strong> or <strong>Obfuscate</strong> them, replacing the real text with `[REDACTED]` or a fake name in the processed version.
                            </p>
                        </div>
                    </div>

                    {/* Editing */}
                    <div className="flex items-start gap-4">
                        <div className="p-2 bg-zinc-100 dark:bg-zinc-800 rounded-lg shrink-0">
                            <Edit3 className="h-5 w-5 text-zinc-700 dark:text-zinc-300" />
                        </div>
                        <div>
                            <h4 className="font-semibold text-sm mb-1">Editing Transcripts</h4>
                            <p className="text-sm text-zinc-500">
                                Switch between "Original" and "Edited" tabs to see changes.
                                Click "Edit Text" to fix typos. After editing, click <strong>Run Pipeline</strong> to update the PII detection and segments based on your changes.
                            </p>
                        </div>
                    </div>

                    {/* Deletion */}
                    <div className="flex items-start gap-4">
                        <div className="p-2 bg-red-50 dark:bg-red-950/30 rounded-lg shrink-0">
                            <Trash2 className="h-5 w-5 text-red-600 dark:text-red-400" />
                        </div>
                        <div>
                            <h4 className="font-semibold text-sm mb-1">Deleting Data</h4>
                            <p className="text-sm text-zinc-500">
                                Use the specific <strong>Delete buttons</strong> on each card to remove just the audio, transcript, or segments.
                                Use the main <strong>Delete Recording</strong> button at the top to permanently remove the entire entry.
                            </p>
                        </div>
                    </div>

                </div>
            </DialogContent>
        </Dialog>
    );
}
