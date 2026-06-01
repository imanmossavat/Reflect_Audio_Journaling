"use client"

import { useEffect, useMemo, useState } from "react"
import { useTheme } from "next-themes"
import { AlertTriangle, ExternalLink, Loader2 } from "lucide-react"
import { toast } from "sonner"

import { TopNav } from "@/components/top-nav"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  api,
  type AppDateFormat,
  type AppDevice,
  type AppLanguage,
  type AppSettings,
  type AppTheme,
  type AppWhisperModel,
  type DeviceOption,
  type OllamaModelListing,
  type SpacyModelEntry,
} from "@/lib/api"

const WHISPER_MODELS: { value: AppWhisperModel; label: string }[] = [
  { value: "tiny", label: "tiny — fastest, lowest accuracy" },
  { value: "base", label: "base — small + decent (default)" },
  { value: "small", label: "small — balanced" },
  { value: "medium", label: "medium — slower, better" },
  { value: "large-v3", label: "large-v3 — best, slowest" },
]

const LANGUAGES: { value: AppLanguage; label: string }[] = [
  { value: "en", label: "English" },
  { value: "nl", label: "Dutch (Nederlands)" },
]

const THEMES: { value: AppTheme; label: string }[] = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
]

const DATE_FORMATS: { value: AppDateFormat; label: string }[] = [
  { value: "dmy", label: "Day / Month / Year (e.g. 15-03-2024)" },
  { value: "mdy", label: "Month / Day / Year (e.g. 03-15-2024)" },
]

function FieldLoader({ label }: { label: string }) {
  return (
    <div className="flex h-9 items-center gap-2 px-3 rounded-md border border-input bg-transparent text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  )
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [devices, setDevices] = useState<DeviceOption[]>([])
  const [ollama, setOllama] = useState<OllamaModelListing | null>(null)
  const [spacy, setSpacy] = useState<SpacyModelEntry[]>([])
  const [devicesLoading, setDevicesLoading] = useState(true)
  const [ollamaLoading, setOllamaLoading] = useState(true)
  const [spacyLoading, setSpacyLoading] = useState(true)
  const [savingKey, setSavingKey] = useState<string | null>(null)
  const [hostDraft, setHostDraft] = useState("")
  const [dbPathDraft, setDbPathDraft] = useState("")
  const { theme, setTheme } = useTheme()

  useEffect(() => {
    void loadAll()
  }, [])

  async function loadAll() {
    // Block the initial paint only on /settings itself — the rest of the
    // endpoints (devices, ollama, spacy) can take a few seconds and we
    // don't want them holding up the form skeleton.
    try {
      const s = await api.getSettings()
      setSettings(s)
      setHostDraft(s.ollama_host)
      setDbPathDraft(s.db_path)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load settings")
      return
    }

    void api
      .listDevices()
      .then(setDevices)
      .catch((err) => toast.error(err instanceof Error ? err.message : "Failed to load devices"))
      .finally(() => setDevicesLoading(false))
    void api
      .listOllamaModels()
      .then(setOllama)
      .catch(() => {
        // Ollama unreachable is rendered inline by the chat-model section.
      })
      .finally(() => setOllamaLoading(false))
    void api
      .listSpacyModels()
      .then(setSpacy)
      .catch(() => {})
      .finally(() => setSpacyLoading(false))
  }

  async function persist<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    if (!settings || settings[key] === value) return
    setSavingKey(String(key))
    try {
      const updated = await api.updateSettings({ [key]: value } as Partial<AppSettings>)
      setSettings(updated)
      toast.success(`Saved ${key.toString().replace("_", " ")}`)
      if (key === "ollama_host") {
        const o = await api.listOllamaModels()
        setOllama(o)
      }
      if (key === "language") {
        const sp = await api.listSpacyModels()
        setSpacy(sp)
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save")
    } finally {
      setSavingKey(null)
    }
  }

  const spacyForCurrent = useMemo(() => {
    if (!settings) return null
    return spacy.find((s) => s.language === settings.language) ?? null
  }, [settings, spacy])

  const selectedDevice = useMemo(() => {
    if (!settings) return null
    return devices.find((d) => d.id === settings.device) ?? null
  }, [settings, devices])

  return (
    <div className="min-h-screen bg-background">
      <TopNav activePath="/settings" />

      <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Settings</h1>
          <p className="text-sm text-muted-foreground">
            These settings apply to the backend running on this machine.
          </p>
        </div>

        {/* Chat */}
        <Card>
          <CardHeader>
            <CardTitle>Chat</CardTitle>
            <CardDescription>Which local LLM answers your questions and splits sources.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Chat model</Label>
              {!settings || ollamaLoading ? (
                <FieldLoader label="Looking for installed models…" />
              ) : ollama?.available && ollama.models.length > 0 ? (
                <Select
                  value={settings.chat_model}
                  onValueChange={(v) => persist("chat_model", v)}
                  disabled={savingKey === "chat_model"}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a model" />
                  </SelectTrigger>
                  <SelectContent>
                    {ollama.models.map((m) => (
                      <SelectItem key={m.name} value={m.name}>
                        {m.name}
                      </SelectItem>
                    ))}
                    {!ollama.models.some((m) => m.name === settings.chat_model) && (
                      <SelectItem value={settings.chat_model}>
                        {settings.chat_model} (not installed)
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              ) : (
                <div className="text-sm rounded-md border border-amber-300/60 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-900/50 p-3">
                  <p className="flex items-center gap-2 font-medium">
                    <AlertTriangle className="h-4 w-4" /> Ollama isn't reachable at {settings.ollama_host}
                  </p>
                  <p className="text-muted-foreground mt-1">
                    Install Ollama, then pull a model.{" "}
                    <a
                      href="https://ollama.com/download"
                      target="_blank"
                      rel="noreferrer"
                      className="underline inline-flex items-center gap-1"
                    >
                      Get Ollama <ExternalLink className="h-3 w-3" />
                    </a>
                  </p>
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                Browse models at{" "}
                <a
                  href="https://ollama.com/library"
                  target="_blank"
                  rel="noreferrer"
                  className="underline"
                >
                  ollama.com/library
                </a>
                . Pull any model with{" "}
                <code className="font-mono">ollama pull &lt;name&gt;</code>.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="ollama-host">Ollama host</Label>
              <div className="flex gap-2">
                <Input
                  id="ollama-host"
                  value={hostDraft}
                  onChange={(e) => setHostDraft(e.target.value)}
                  placeholder="http://localhost:11434"
                />
                <Button
                  variant="outline"
                  disabled={!settings || savingKey === "ollama_host" || hostDraft === settings.ollama_host}
                  onClick={() => persist("ollama_host", hostDraft)}
                >
                  Save
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Transcription */}
        <Card>
          <CardHeader>
            <CardTitle>Transcription</CardTitle>
            <CardDescription>WhisperX settings for audio sources.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Compute device</Label>
              {!settings || devicesLoading ? (
                <FieldLoader label="Detecting hardware…" />
              ) : (
                <Select
                  value={settings.device}
                  onValueChange={(v) => persist("device", v as AppDevice)}
                  disabled={savingKey === "device"}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {devices.map((d) => (
                      <SelectItem key={d.id} value={d.id} disabled={!d.available}>
                        <span className="flex flex-col text-left">
                          <span>
                            {d.label}
                            {!d.available && " — not detected"}
                            {d.available && !d.supported_for_transcription && " — falls back to CPU"}
                          </span>
                          {d.detail && (
                            <span className="text-xs text-muted-foreground">{d.detail}</span>
                          )}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              {selectedDevice && !selectedDevice.supported_for_transcription && (
                <p className="text-xs text-amber-700 dark:text-amber-300">
                  WhisperX uses CTranslate2, which only supports CPU and CUDA. {selectedDevice.label}{" "}
                  will fall back to CPU for transcription.
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Whisper model</Label>
              {!settings ? (
                <FieldLoader label="Loading…" />
              ) : (
                <Select
                  value={settings.whisper_model}
                  onValueChange={(v) => persist("whisper_model", v as AppWhisperModel)}
                  disabled={savingKey === "whisper_model"}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {WHISPER_MODELS.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            <div className="space-y-2">
              <Label>Language</Label>
              {!settings ? (
                <FieldLoader label="Loading…" />
              ) : (
                <Select
                  value={settings.language}
                  onValueChange={(v) => persist("language", v as AppLanguage)}
                  disabled={savingKey === "language"}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {LANGUAGES.map((l) => (
                      <SelectItem key={l.value} value={l.value}>
                        {l.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <p className="text-xs text-muted-foreground">
                Also switches the spaCy model used when splitting sources into chunks.
              </p>
              {!spacyLoading && spacyForCurrent && !spacyForCurrent.installed && (
                <div className="text-sm rounded-md border border-amber-300/60 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-900/50 p-3">
                  <p className="flex items-center gap-2 font-medium">
                    <AlertTriangle className="h-4 w-4" /> spaCy model {spacyForCurrent.model} not installed
                  </p>
                  <p className="text-muted-foreground mt-1">
                    Run{" "}
                    <code className="font-mono">
                      python -m spacy download {spacyForCurrent.model}
                    </code>{" "}
                    on the backend.
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Data */}
        <Card>
          <CardHeader>
            <CardTitle>Data</CardTitle>
            <CardDescription>Where your sources live, and how to take them with you.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="db-path">Database path</Label>
              <div className="flex gap-2">
                <Input
                  id="db-path"
                  value={dbPathDraft}
                  onChange={(e) => setDbPathDraft(e.target.value)}
                />
                <Button
                  variant="outline"
                  disabled={!settings || savingKey === "db_path" || dbPathDraft === settings.db_path}
                  onClick={() => persist("db_path", dbPathDraft)}
                >
                  Save
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Changing this requires a backend restart and won't migrate existing data.
              </p>
            </div>

            <div className="space-y-2">
              <Label>Date format</Label>
              {!settings ? (
                <FieldLoader label="Loading…" />
              ) : (
                <Select
                  value={settings.date_format}
                  onValueChange={(v) => persist("date_format", v as AppDateFormat)}
                  disabled={savingKey === "date_format"}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DATE_FORMATS.map((f) => (
                      <SelectItem key={f.value} value={f.value}>
                        {f.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <p className="text-xs text-muted-foreground">
                How dates are read from uploaded filenames. Year-first names
                (e.g. 2024-03-15) are detected automatically.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <Button variant="outline" disabled>
                Export data (coming soon)
              </Button>
              <Button variant="destructive" disabled>
                Delete all data (coming soon)
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Appearance */}
        <Card>
          <CardHeader>
            <CardTitle>Appearance</CardTitle>
            <CardDescription>How the app looks in this browser.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Theme</Label>
              <Select
                value={(theme as AppTheme | undefined) ?? settings?.theme ?? "system"}
                onValueChange={(v) => {
                  setTheme(v)
                  void persist("theme", v as AppTheme)
                }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {THEMES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
