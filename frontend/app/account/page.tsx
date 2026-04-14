"use client"

import { useEffect, useMemo, useState } from "react"
import { Settings, Download, Shield, Bell, ChevronRight } from "lucide-react"
import { ActivityCalendar } from "@/components/activity-calendar"
import { TopNav } from "@/components/top-nav"
import { api, type SourceRecord } from "@/lib/api"

const profileStorageKey = "reflect_profile"

export default function AccountPage() {
  const [activeTab, setActiveTab] = useState<"overview" | "settings" | "privacy">("overview")
  const [sources, setSources] = useState<SourceRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [profileName, setProfileName] = useState("You")

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      try {
        const allSources = await api.getSources()
        setSources(allSources)
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error")
      } finally {
        setLoading(false)
      }
    }

    const stored = window.localStorage.getItem(profileStorageKey)
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as { name?: string }
        if (parsed.name) setProfileName(parsed.name)
      } catch {
        // Ignore invalid local profile data.
      }
    }

    void loadData()
  }, [])

  const activityData = useMemo(() => {
    const data: Record<string, number> = {}
    for (const source of sources) {
      const dateKey = new Date(source.created_at).toISOString().split("T")[0]
      data[dateKey] = (data[dateKey] ?? 0) + 1
    }
    return data
  }, [sources])

  const totalEntries = sources.length
  const activeDays = Object.keys(activityData).length
  const dayStreak = useMemo(() => {
    let streak = 0
    const cursor = new Date()
    while (true) {
      const key = cursor.toISOString().split("T")[0]
      if (!activityData[key]) break
      streak += 1
      cursor.setDate(cursor.getDate() - 1)
    }
    return streak
  }, [activityData])

  return (
    <div className="min-h-screen bg-background">
      <TopNav activePath="/account" />

      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Profile Header */}
        <div className="flex items-center gap-4 mb-8">
          <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
            <span className="text-2xl font-semibold text-emerald-600">{profileName[0]?.toUpperCase() ?? "Y"}</span>
          </div>
          <div>
            <h1 className="text-xl font-semibold">{profileName}</h1>
            <p className="text-muted-foreground">Tracking sources from your backend data</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b mb-8">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === "overview"
                ? "border-b-2 border-emerald-500 text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab("settings")}
            className={`px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === "settings"
                ? "border-b-2 border-emerald-500 text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Settings
          </button>
          <button
            onClick={() => setActiveTab("privacy")}
            className={`px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === "privacy"
                ? "border-b-2 border-emerald-500 text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Privacy
          </button>
        </div>

        {activeTab === "overview" && (
          <div className="space-y-8">
            {loading && <p className="text-sm text-muted-foreground">Loading account data...</p>}
            {error && <p className="text-sm text-red-600">Could not load data: {error}</p>}
            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="p-5 rounded-xl border bg-card">
                <div className="text-3xl font-semibold text-emerald-600">{totalEntries}</div>
                <div className="text-sm text-muted-foreground mt-1">Total reflections</div>
              </div>
              <div className="p-5 rounded-xl border bg-card">
                <div className="text-3xl font-semibold text-emerald-600">{activeDays}</div>
                <div className="text-sm text-muted-foreground mt-1">Active days</div>
              </div>
              <div className="p-5 rounded-xl border bg-card">
                <div className="text-3xl font-semibold text-emerald-600">{dayStreak}</div>
                <div className="text-sm text-muted-foreground mt-1">Day streak</div>
              </div>
            </div>

            {/* Activity Calendar */}
            <div className="p-6 rounded-xl border bg-card">
              <h2 className="font-medium mb-4">Your activity</h2>
              <ActivityCalendar 
                data={activityData} 
                onDateClick={(date) => console.log("Navigate to", date)} 
              />
            </div>

            {/* Recent Insights */}
            <div className="p-6 rounded-xl border bg-card">
              <h2 className="font-medium mb-4">Insights</h2>
              <div className="space-y-3">
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm">You have created <span className="font-medium text-emerald-600">{totalEntries}</span> total source entries.</p>
                </div>
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm">You were active on <span className="font-medium text-emerald-600">{activeDays}</span> distinct day{activeDays === 1 ? "" : "s"}.</p>
                </div>
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm">Current streak: <span className="font-medium">{dayStreak} day{dayStreak === 1 ? "" : "s"}</span>.</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "settings" && (
          <div className="space-y-4">
            <button className="w-full flex items-center justify-between p-4 rounded-xl border bg-card hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                  <Bell className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="text-left">
                  <div className="font-medium">Notifications</div>
                  <div className="text-sm text-muted-foreground">Daily reminders and insights</div>
                </div>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </button>

            <button className="w-full flex items-center justify-between p-4 rounded-xl border bg-card hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                  <Download className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="text-left">
                  <div className="font-medium">Export data</div>
                  <div className="text-sm text-muted-foreground">Download all your reflections</div>
                </div>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </button>

            <button className="w-full flex items-center justify-between p-4 rounded-xl border bg-card hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                  <Settings className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="text-left">
                  <div className="font-medium">Preferences</div>
                  <div className="text-sm text-muted-foreground">Theme, language, and more</div>
                </div>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </button>
          </div>
        )}

        {activeTab === "privacy" && (
          <div className="space-y-6">
            <div className="p-6 rounded-xl border bg-card">
              <div className="flex items-center gap-3 mb-4">
                <Shield className="h-5 w-5 text-emerald-600" />
                <h2 className="font-medium">Your data is yours</h2>
              </div>
              <div className="space-y-4 text-sm text-muted-foreground">
                <p>All your source entries are encrypted end-to-end. Only you can read them.</p>
                <p>We never sell your data or use it for advertising. Your reflections are never used to train AI models without explicit consent.</p>
                <p>You can delete all your data at any time, and it will be permanently removed from our servers.</p>
              </div>
            </div>

            <div className="space-y-3">
              <button className="w-full flex items-center justify-between p-4 rounded-xl border bg-card hover:bg-muted/50 transition-colors">
                <div className="text-left">
                  <div className="font-medium">Download my data</div>
                  <div className="text-sm text-muted-foreground">Get a copy of everything</div>
                </div>
                <ChevronRight className="h-5 w-5 text-muted-foreground" />
              </button>
              
              <button className="w-full flex items-center justify-between p-4 rounded-xl border border-red-200 dark:border-red-900 bg-card hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors">
                <div className="text-left">
                  <div className="font-medium text-red-600">Delete all data</div>
                  <div className="text-sm text-muted-foreground">Permanently remove everything</div>
                </div>
                <ChevronRight className="h-5 w-5 text-red-400" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
