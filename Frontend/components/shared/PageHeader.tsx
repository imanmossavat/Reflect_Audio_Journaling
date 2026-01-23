"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import ServerStatus from "./ServerStatus";

interface PageHeaderProps {
    title: string;
    description?: string;
}

export default function PageHeader({ title, description }: PageHeaderProps) {
    return (
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
            <div className="flex items-start gap-4">
                <Link href="/" className="mt-1 p-2 rounded-full hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors">
                    <ArrowLeft className="h-5 w-5 text-zinc-600 dark:text-zinc-400" />
                </Link>
                <div>
                    <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-100">{title}</h1>
                    {description && <p className="text-sm text-zinc-500 mt-1">{description}</p>}
                </div>
            </div>

            <ServerStatus />
        </div>
    );
}
