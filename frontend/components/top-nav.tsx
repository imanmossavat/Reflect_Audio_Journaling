"use client"

import { Home, User } from "lucide-react"
import Link from "next/link"

type TopNavProps = {
  activePath: "/" | "/account"
}

export function TopNav({ activePath }: TopNavProps) {
  const sourceActive = activePath === "/"
  const accountActive = activePath === "/account"

  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
      <div className="px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="font-semibold text-lg tracking-tight">
            REFLECT
          </Link>
          <div className="flex items-center gap-1">
            <Link
              href="/"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors ${
                sourceActive
                  ? "font-medium bg-muted"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              <Home className="h-4 w-4" />
              Home
            </Link>
            <Link
              href="/account"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors ${
                accountActive
                  ? "font-medium bg-muted"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              <User className="h-4 w-4" />
              Account
            </Link>
          </div>
        </div>
      </div>
    </nav>
  )
}
