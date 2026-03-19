"use client";

import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Save, RefreshCw, Trash2, Settings } from "lucide-react";
import Link from "next/link";

interface SettingsActionsProps {
    saving: boolean;
    onSave: (forceRestart: boolean) => void;
    onReset: () => void;
}

export default function SettingsActions({ saving, onSave, onReset }: SettingsActionsProps) {
    return (
        <Card className="border-zinc-200 dark:border-zinc-800 shadow-sm">
            <CardHeader><CardTitle className="text-[10px] font-bold uppercase text-zinc-500">Actions</CardTitle></CardHeader>
            <CardContent className="space-y-2">
                <Button className="w-full justify-start text-xs h-9" onClick={() => onSave(false)} disabled={saving}>
                    <Save className="h-3.5 w-3.5 mr-2" /> Save Changes
                </Button>
                <Button variant="outline" className="w-full justify-start text-xs h-9 border-amber-200 text-amber-700 hover:bg-amber-50" onClick={() => onSave(true)} disabled={saving}>
                    <RefreshCw className="h-3.5 w-3.5 mr-2" /> Save & Restart
                </Button>
                <Separator className="my-2" />
                <Button variant="ghost" className="w-full justify-start text-xs h-9 text-zinc-400 hover:text-red-600" onClick={onReset} disabled={saving}>
                    <Trash2 className="h-3.5 w-3.5 mr-2" /> Reset to Defaults
                </Button>
                <Link href="/setup?reconfigure=true" className="block w-full">
                    <Button variant="ghost" className="w-full justify-start text-xs h-9 text-indigo-500 hover:text-indigo-600 hover:bg-indigo-50">
                        <Settings className="h-3.5 w-3.5 mr-2" /> Run Setup Wizard
                    </Button>
                </Link>
            </CardContent>
        </Card>
    );
}
