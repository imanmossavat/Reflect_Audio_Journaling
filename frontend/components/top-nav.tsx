"use client"

import { Home, Settings, User } from "lucide-react"
import Link from "next/link"

type TopNavProps = {
  activePath: "/" | "/account" | "/settings"
}

export function TopNav({ activePath }: TopNavProps) {
  const links: Array<{ href: TopNavProps["activePath"]; label: string; icon: typeof Home }> = [
    { href: "/", label: "Home", icon: Home },
    { href: "/account", label: "Account", icon: User },
    { href: "/settings", label: "Settings", icon: Settings },
  ]

  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
      <div className="px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="font-semibold text-lg tracking-tight">
            REFLECT
          </Link>
          <div className="flex items-center gap-1">
            {links.map(({ href, label, icon: Icon }) => {
              const isActive = activePath === href
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors ${
                    isActive
                      ? "font-medium bg-muted"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              )
            })}
          </div>
        </div>
      </div>
    </nav>
  )
}
