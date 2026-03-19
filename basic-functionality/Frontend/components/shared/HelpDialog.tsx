import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { HelpCircle, MoreHorizontal, Search, Sparkles, Filter, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";

export function HelpDialog() {
    return (
        <Dialog>
            <DialogTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2 text-zinc-500">
                    <HelpCircle className="h-4 w-4" />
                    <span className="hidden md:inline">Help</span>
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Library Guide</DialogTitle>
                    <DialogDescription>
                        How to use search, filters, and manage your recordings.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-8 pt-4">

                    {/* Actions */}
                    <div className="flex items-start gap-4">
                        <div className="p-2 bg-zinc-100 dark:bg-zinc-800 rounded-lg shrink-0">
                            <MoreHorizontal className="h-5 w-5 text-zinc-700 dark:text-zinc-300" />
                        </div>
                        <div>
                            <h4 className="font-semibold text-sm mb-1">Actions Menu</h4>
                            <p className="text-sm text-zinc-500">
                                Click the three dots on any recording card to access options like <strong>delete</strong>.
                                This menu is always visible.
                            </p>
                        </div>
                    </div>

                    {/* Semantic Search */}
                    <div className="flex items-start gap-4">
                        <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg shrink-0">
                            <Sparkles className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                        </div>
                        <div>
                            <h4 className="font-semibold text-sm mb-1">Semantic Search (Search by Meaning)</h4>
                            <p className="text-sm text-zinc-500">
                                Use the second search bar to find recordings based on <strong>concepts or mood</strong> rather than exact keywords.
                                <br />Example: <em>"I felt really stressed about my project"</em> will find entries where you talked about anxiety or deadlines, even if you never used those exact words.
                            </p>
                        </div>
                    </div>

                    {/* Standard Search */}
                    <div className="flex items-start gap-4">
                        <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg shrink-0">
                            <Search className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                            <h4 className="font-semibold text-sm mb-1">Keyword Search</h4>
                            <p className="text-sm text-zinc-500">
                                The top search bar looks for exact matches in <strong>Titles, Tags, and Transcripts</strong>.
                            </p>
                        </div>
                    </div>

                    {/* Filters */}
                    <div className="flex items-start gap-4">
                        <div className="p-2 bg-orange-50 dark:bg-orange-900/20 rounded-lg shrink-0">
                            <Filter className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                        </div>
                        <div>
                            <h4 className="font-semibold text-sm mb-1">Advanced Filters</h4>
                            <div className="text-sm text-zinc-500 space-y-1 mt-1">
                                <p><strong>Date Range:</strong> Pick a start and end date to narrow down history.</p>
                                <p><strong>Status:</strong> Find original, edited, or redacted entries.</p>
                                <p><strong>Audio:</strong> Filter for entries that have audio files attached vs text-only.</p>
                                <p><strong>Tags:</strong> Select multiple tags to find entries matching all of them.</p>
                            </div>
                        </div>
                    </div>

                </div>
            </DialogContent>
        </Dialog>
    );
}
