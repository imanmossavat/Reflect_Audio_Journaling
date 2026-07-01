export type SourceStatus =
  | "processed"
  | "not processed"
  | "queued"
  | "transcribing"
  | "chunking"
  | "indexing"
  | "failed"
  | "failed_no_speech"
  | "failed_ollama_not_running"
  | "failed_ollama_not_installed"
  | "failed_ollama_model_missing"
  | string

export const PROCESSING_STATUSES = new Set<SourceStatus>(["queued", "transcribing", "chunking", "indexing"])

export const OLLAMA_FAILURE_STATUSES = new Set<SourceStatus>([
  "failed_ollama_not_running",
  "failed_ollama_not_installed",
  "failed_ollama_model_missing",
])

export const PROCESSING_STATUS_LABELS: Record<string, string> = {
  queued: "Queued...",
  transcribing: "Transcribing audio...",
  chunking: "Splitting into chunks...",
  indexing: "Building search index...",
  failed: "Processing failed",
  failed_no_speech: "Failed — no speech detected",
  failed_ollama_not_running: "Failed — Ollama is not running",
  failed_ollama_not_installed: "Failed — Ollama is not installed",
  failed_ollama_model_missing: "Failed — embedding model missing",
}

export const EMBED_MODEL_NAME = "nomic-embed-text"

export interface FailureExplanation {
  title: string
  description: string
  command?: string
}

export function explainFailure(status: SourceStatus): FailureExplanation | null {
  switch (status) {
    case "failed_ollama_not_installed":
      return {
        title: "Ollama isn't installed",
        description:
          "Reflect uses Ollama to generate the embeddings that power semantic search. Install it from ollama.com, then click Retry.",
      }
    case "failed_ollama_not_running":
      return {
        title: "Ollama isn't running",
        description:
          "Reflect could reach the embedding step but Ollama wasn't responding. Start the Ollama app (or run `ollama serve`), then click Retry.",
        command: "ollama serve",
      }
    case "failed_ollama_model_missing":
      return {
        title: `The embedding model "${EMBED_MODEL_NAME}" isn't installed`,
        description:
          "Reflect needs this model to index your sources. Pull it once in a terminal, then click Retry.",
        command: `ollama pull ${EMBED_MODEL_NAME}`,
      }
    case "failed_no_speech":
      return {
        title: "No speech detected",
        description:
          "The audio loaded fine, but we couldn't find any spoken words to transcribe — the recording may be silent or empty. Check the audio (or try a different language / Whisper model in Settings), then click Retry.",
      }
    case "failed":
      return {
        title: "Processing failed",
        description:
          "Something went wrong while indexing this source. Check the backend logs for details, then click Retry.",
      }
    default:
      return null
  }
}

export interface TranscriptSegment {
  text: string
  start_s: number | null
  end_s: number | null
}

export interface SourceRecord {
  id: number
  filename: string | null
  file_type: string | null
  text: string | null
  text_html: string | null
  transcript_segments: TranscriptSegment[] | null
  summary: string | null
  summary_html: string | null
  status: SourceStatus
  created_at: string
}

export interface SourceTag {
  id: number
  name: string
}

export interface SourceChunk {
  id: number
  chunk_index: number
  chunk_text: string
}

export interface TagSourceMembership {
  id: number
  filename: string | null
  file_type: string | null
}

export interface TagWithSources {
  id: number
  name: string
  sources: TagSourceMembership[]
}

export interface QuerySource {
  source_id?: string | null
  chunk_id?: string | null
  score?: number | null
  node_id?: string | null
  text: string
}

export interface QueryResponse {
  question: string
  answer: string
  sources: QuerySource[]
  model_used: string | null
}

export interface SaveAnswerRequest {
  source_id: number
  question_text: string
  answer_text: string
}

export type ChatMessageRole = "question" | "answer"

export interface ChatMessageRecord {
  id: number
  chat_id: number
  role: ChatMessageRole
  text: string
  scale_value: number | null
  scale_max: number | null
  scale_low_label: string | null
  scale_high_label: string | null
  model: string | null
  thinking: string | null
  /** Gibbs stage (1-6) this message belongs to during guided reflection; null otherwise. */
  gibbs_step: number | null
  /** Retrieved sources backing a RAG ("context question") answer; null otherwise. */
  sources: QuerySource[] | null
  created_at: string
}

export type ChatStreamStageName = "checking" | "queued" | "searching" | "retrieved" | "thinking" | "writing"

/** Care pathway a guard hit maps to — drives which support card the UI shows. */
export type SafetyKind = "self_harm" | "support"

/** The mandatory guard model isn't installed — drives the in-chat "set up the guard" card. */
export interface GuardUnavailableInfo {
  model: string
  command: string
}

export interface SafetyVerdict {
  flagged: boolean
  kind: SafetyKind | null
  categories: string[]
}

export interface ChatStreamHandlers {
  onStage: (stage: { name: ChatStreamStageName; count?: number }) => void
  /** Cumulative answer length so the UI can grow a skeleton; the real text stays
   *  server-side until the output guard passes (then it arrives via onDone + refetch). */
  onProgress: (chars: number) => void
  onSources?: (sources: QuerySource[]) => void
  onDone: (info: { model: string | null; message_id: number }) => void
  /** Guard tripped (input intercept or blocked output): show a support card, no answer. */
  onFallback: (kind: SafetyKind) => void
  /** Guard model isn't installed: the guard is mandatory, so we can't answer. Show a setup
   *  card (in-thread, like a support card) with the install command — not a hard error. */
  onGuardUnavailable?: (info: GuardUnavailableInfo) => void
  onError: (error: Error) => void
  // Emitted by a resume stream when no generation is active for the chat, so the
  // caller can fall back to a normal chat load instead of waiting on tokens.
  onIdle?: () => void
}

export interface ActiveGeneration {
  chat_id: number
  status: string
}

/** A topic group proposed from the selected sources during reflection setup. */
export interface TopicGroup {
  name: string
  summary: string
  items: string[]
}

/** The chosen scope persisted on a reflection chat. */
export interface ReflectionScope {
  topic: string
  items: string[]
  source_ids?: number[]
}

export interface ChatSummary {
  id: number
  title: string
  source_id: number | null
  reflection_goal: string | null
  reflection_scope: ReflectionScope | null
  message_count: number
  edited_at: string
  created_at: string
}

export interface ChatDetail {
  id: number
  title: string
  source_id: number | null
  reflection_goal: string | null
  reflection_scope: ReflectionScope | null
  created_at: string
  edited_at: string
  messages: ChatMessageRecord[]
}

export interface AppendChatMessagePayload {
  role: ChatMessageRole
  text: string
  scale_value?: number | null
  scale_max?: number | null
  scale_low_label?: string | null
  scale_high_label?: string | null
  model?: string | null
  gibbs_step?: number | null
}

type GenerateQuestionMode = "clarifying" | "deep_dive" | "reply" | "reflect"

export interface GenerateQuestionRequest {
  mode: GenerateQuestionMode
  // Identifies the reflection_state row this turn reads/writes (Document B §2).
  chat_id: number
  step?: number
  focus_tag?: string
  focus_tag_summary?: string
  history?: Array<Record<string, unknown>>
  journal_text?: string
  goal?: string
  scope_items?: string[]
}

export type AppDevice = "cpu" | "cuda" | "mps" | "rocm"
export type AppLanguage = "en" | "nl"
export type AppWhisperModel = "tiny" | "base" | "small" | "medium" | "large-v3"
export type AppTheme = "light" | "dark" | "system"
export type AppDateFormat = "dmy" | "mdy"

export interface AppSettings {
  chat_model: string
  embed_model: string
  ollama_host: string
  device: AppDevice
  whisper_model: AppWhisperModel
  language: AppLanguage
  db_path: string
  theme: AppTheme
  date_format: AppDateFormat
}

export interface DeviceOption {
  id: AppDevice
  label: string
  available: boolean
  detail: string | null
  supported_for_transcription: boolean
}

export interface OllamaModelEntry {
  name: string
  size?: number
}

export interface OllamaModelListing {
  available: boolean
  host: string
  models: OllamaModelEntry[]
  error?: string
}

export interface SpacyModelEntry {
  language: AppLanguage
  model: string
  installed: boolean
}

function getBackendBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "")
  if (configured) {
    return configured
  }

  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "https:" : "http:"
    const host = window.location.hostname
    const port = process.env.NEXT_PUBLIC_BACKEND_PORT ?? "8000"
    return `${protocol}//${host}:${port}`
  }

  return "http://localhost:8000"
}

function withTimeout(timeoutMs: number): { signal: AbortSignal; cancel: () => void } {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  return {
    signal: controller.signal,
    cancel: () => clearTimeout(timeoutId),
  }
}


// Read an SSE chat stream (POST /query-stream or GET resume) to completion, dispatching
// each `data:` event to the handlers. Shared by streamQuery and subscribeGeneration so
// the parsing lives in one place.
async function consumeChatStream(response: Response, handlers: ChatStreamHandlers): Promise<void> {
  if (!response.ok || !response.body) {
    throw new Error(`Unable to stream answer (${response.status})`)
  }

  const decoder = new TextDecoder()
  const reader = response.body.getReader()
  let buffer = ""

  const dispatch = (raw: string) => {
    const trimmed = raw.trim()
    if (!trimmed) return
    let parsed: Record<string, unknown>
    try {
      parsed = JSON.parse(trimmed) as Record<string, unknown>
    } catch {
      return
    }
    const eventType = parsed.type as string | undefined
    switch (eventType) {
      case "stage":
        handlers.onStage({
          name: parsed.name as ChatStreamStageName,
          count: typeof parsed.count === "number" ? parsed.count : undefined,
        })
        break
      case "progress":
        if (typeof parsed.chars === "number") handlers.onProgress(parsed.chars)
        break
      case "sources":
        handlers.onSources?.(parsed.sources as QuerySource[])
        break
      case "done":
        handlers.onDone({
          model: (parsed.model as string | null) ?? null,
          message_id: parsed.message_id as number,
        })
        break
      case "fallback":
        handlers.onFallback((parsed.kind as SafetyKind) || "support")
        break
      case "guard_unavailable":
        handlers.onGuardUnavailable?.({
          model: (parsed.model as string) || "",
          command: (parsed.command as string) || "",
        })
        break
      case "error":
        handlers.onError(new Error((parsed.detail as string) || "Stream error"))
        break
      case "idle":
        handlers.onIdle?.()
        break
    }
  }

  const drainEvents = (chunk: string) => {
    for (const line of chunk.split(/\r?\n/)) {
      if (line.startsWith("data:")) dispatch(line.slice(5).trim())
    }
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split(/\r?\n\r?\n/)
    buffer = events.pop() ?? ""
    for (const evt of events) drainEvents(evt)
  }
  if (buffer.trim()) drainEvents(buffer)
}

async function request<T>(path: string, init?: RequestInit, timeoutMs: number = 20000): Promise<T> {
  const timeout = withTimeout(timeoutMs)
  try {
    const response = await fetch(`${getBackendBaseUrl()}${path}`, {
      ...init,
      signal: timeout.signal,
      credentials: "include",
    })

    if (!response.ok) {
      const body = await response.text().catch(() => "")
      let message = body || response.statusText
      try {
        const parsed = JSON.parse(body) as { detail?: string }
        if (parsed.detail) {
          message = parsed.detail
        }
      } catch {
        // Body was not JSON, keep original message.
      }
      throw new Error(`API ${response.status}: ${message}`)
    }

    if (response.status === 204) {
      return undefined as T
    }

    return (await response.json()) as T
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Request timed out. Make sure the backend is running and reachable.")
    }
    throw error
  } finally {
    timeout.cancel()
  }
}

export const api = {
  getSourceAudioUrl(sourceId: number): string {
    return `${getBackendBaseUrl()}/source/${sourceId}/audio`
  },
  getSources(sinceId = 0) {
    const url = sinceId > 0 ? `/sources?since_id=${sinceId}` : "/sources"
    return request<SourceRecord[]>(url)
  },
  getUnprocessedSources() {
    return request<SourceRecord[]>("/unprocessed-sources")
  },
  getSourceById(sourceId: number) {
    return request<SourceRecord>(`/source/${sourceId}`)
  },
  getSourceText(sourceId: number) {
    return request<string>(`/source-text/${sourceId}`)
  },
  getSourceChunks(sourceId: number) {
    return request<SourceChunk[]>(`/source/${sourceId}/chunks`)
  },
  uploadRawTextSource(sourceText: string) {
    const body = new FormData()
    body.append("source_text", sourceText)
    return request<SourceRecord>("/source/uploadText/raw", {
      method: "POST",
      body,
    })
  },
  uploadProcessedTextSource(sourceText: string, sourceHtml?: string) {
    const body = new FormData()
    body.append("source_text", sourceText)
    if (sourceHtml != null) body.append("source_html", sourceHtml)
    return request<SourceRecord>("/source/uploadText/processed", {
      method: "POST",
      body,
    })
  },
  uploadTextSource(sourceText: string, processed = false, sourceHtml?: string) {
    if (processed) {
      return this.uploadProcessedTextSource(sourceText, sourceHtml)
    }
    return this.uploadRawTextSource(sourceText)
  },
  uploadRawFileSource(file: File) {
    const body = new FormData()
    body.append("file", file)
    return request<SourceRecord>("/source/uploadFile/raw", {
      method: "POST",
      body,
    })
  },
  uploadProcessedFileSource(file: File) {
    const body = new FormData()
    body.append("file", file)
    return request<SourceRecord>("/source/uploadFile/processed", {
      method: "POST",
      body,
    })
  },
  uploadFileSource(file: File, processed = false) {
    if (processed) {
      return this.uploadProcessedFileSource(file)
    }
    return this.uploadRawFileSource(file)
  },
  dropFileToInbox(file: File) {
    const body = new FormData()
    body.append("file", file)
    return request<{ queued: boolean; filename: string }>("/source/drop-to-inbox", {
      method: "POST",
      body,
    })
  },
  dropTextToInbox(sourceText: string) {
    const body = new FormData()
    body.append("source_text", sourceText)
    return request<{ queued: boolean; filename: string }>("/source/drop-text-to-inbox", {
      method: "POST",
      body,
    })
  },
  transcribeSource(sourceId: number) {
    return request<SourceRecord>(`/source/transcribe/${sourceId}`, { method: "POST" }).catch((error) => {
      if (error instanceof Error && error.message.includes("API 501")) {
        throw new Error("Transcription is not available in this environment yet. You can still upload text sources.")
      }
      throw error
    })
  },
  patchSource(sourceId: number, fields: { text?: string; text_html?: string; summary?: string; summary_html?: string; filename?: string; created_at?: string }) {
    return request<SourceRecord>(`/source/${sourceId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fields),
    })
  },
  deleteSource(sourceId: number) {
    return request<{ ok: boolean }>(`/source/${sourceId}`, { method: "DELETE" })
  },
  processSource(sourceId: number) {
    return request<SourceRecord>(`/source/process/${sourceId}`, { method: "POST" }, 600000)
  },
  regenerateSummary(sourceId: number) {
    return request<SourceRecord>(`/source/${sourceId}/summary/regenerate`, { method: "POST" }, 600000)
  },
  previewSummary(sourceId: number) {
    return request<{ summary: string }>(`/source/${sourceId}/summary/preview`, { method: "POST" }, 600000)
  },
  query(question: string, top_k = 5) {
    return request<QueryResponse>("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k }),
    }, 120000)
  },
  extractTags(sourceId: number) {
    return request<{ tags: Array<{ name: string; summary: string; quotes: string[] }>; source_text: string }>(
      `/extract-tags?source_id=${sourceId}`,
      { method: "POST" }
    )
  },
  suggestTags(sourceId: number) {
    return request<{ suggestions: Array<{ name: string; reason: string }> }>(
      `/tags/${sourceId}/suggest`,
      { method: "GET" },
      600000,
    )
  },
  getAllTags() {
    return request<SourceTag[]>(`/tags/all`)
  },
  getAllTagsWithSources() {
    return request<TagWithSources[]>(`/tags/all-with-sources`)
  },
  getSourceTags(sourceId: number) {
    return request<SourceTag[]>(`/tags/${sourceId}`)
  },
  addTagToSource(sourceId: number, name: string) {
    return request<SourceTag>(`/tags/${sourceId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    })
  },
  confirmTags(sourceId: number, names: string[]) {
    return request<SourceTag[]>(`/tags/${sourceId}/suggest/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ names }),
    })
  },
  removeTagFromSource(sourceId: number, tagId: number) {
    return request<void>(`/tags/${sourceId}/${tagId}`, { method: "DELETE" })
  },
  saveAnswer(payload: SaveAnswerRequest) {
    return request<{ ok: boolean; question_id: number; answer_id: number }>("/save-answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  },
  listChats() {
    return request<ChatSummary[]>("/chats")
  },
  createChat(title?: string) {
    return request<ChatSummary>("/chats", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: title ?? null }),
    })
  },
  getChat(chatId: number) {
    return request<ChatDetail>(`/chats/${chatId}`)
  },
  renameChat(chatId: number, title: string) {
    return request<ChatSummary>(`/chats/${chatId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    })
  },
  setReflectionGoal(chatId: number, goal: string) {
    return request<ChatSummary>(`/chats/${chatId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reflection_goal: goal }),
    })
  },
  setReflectionScope(chatId: number, scope: ReflectionScope) {
    return request<ChatSummary>(`/chats/${chatId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reflection_scope: scope }),
    })
  },
  groupTopics(journalText: string) {
    return request<{ topics: TopicGroup[] }>("/reflection/topics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ journal_text: journalText }),
    }, 300000)
  },
  deleteChat(chatId: number) {
    return request<{ ok: boolean }>(`/chats/${chatId}`, { method: "DELETE" })
  },
  appendChatMessage(chatId: number, payload: AppendChatMessagePayload) {
    return request<ChatMessageRecord>(`/chats/${chatId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  },
  promoteChat(chatId: number) {
    return request<{ chat: ChatSummary; source: SourceRecord }>(`/chats/${chatId}/promote`, {
      method: "POST",
    }, 600000)
  },
  reindexChat(chatId: number) {
    return request<SourceRecord>(`/chats/${chatId}/reindex`, { method: "POST" }, 600000)
  },
  getOllamaHealth() {
    return request<unknown>("/ollama-health")
  },
  getSettings() {
    return request<AppSettings>("/settings")
  },
  updateSettings(patch: Partial<AppSettings>) {
    return request<AppSettings>("/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    })
  },
  listDevices() {
    return request<DeviceOption[]>("/settings/devices")
  },
  listOllamaModels() {
    return request<OllamaModelListing>("/settings/ollama-models")
  },
  listSpacyModels() {
    return request<SpacyModelEntry[]>("/settings/spacy-models")
  },
  listActiveGenerations() {
    return request<ActiveGeneration[]>("/generations")
  },
  // Screen a user-authored snippet (reflection-writing flow). Never blocks; returns a care
  // `kind` when the text trips a relevant Llama Guard category so the UI can offer support.
  checkSafety(text: string) {
    return request<SafetyVerdict>("/safety/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })
  },
  streamQuery(
    payload: { chatId: number; question: string; top_k?: number },
    handlers: ChatStreamHandlers
  ) {
    const controller = new AbortController()
    const run = async () => {
      try {
        const response = await fetch(`${getBackendBaseUrl()}/query-stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            chat_id: payload.chatId,
            question: payload.question,
            top_k: payload.top_k ?? 5,
          }),
          signal: controller.signal,
          credentials: "include",
        })
        await consumeChatStream(response, handlers)
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return
        handlers.onError(error instanceof Error ? error : new Error("Unknown stream error"))
      }
    }
    void run()
    return () => controller.abort()
  },
  // Re-attach to an in-flight generation (resume after refresh/navigate). Replays the
  // buffered events then streams live; emits `onIdle` if nothing is generating.
  subscribeGeneration(chatId: number, handlers: ChatStreamHandlers) {
    const controller = new AbortController()
    const run = async () => {
      try {
        const response = await fetch(
          `${getBackendBaseUrl()}/chats/${chatId}/generation-stream`,
          { signal: controller.signal, credentials: "include" }
        )
        await consumeChatStream(response, handlers)
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return
        handlers.onError(error instanceof Error ? error : new Error("Unknown stream error"))
      }
    }
    void run()
    return () => controller.abort()
  },
  streamGeneratedQuestion(
    payload: GenerateQuestionRequest,
    handlers: {
      // Cumulative character count so the UI can grow a skeleton (the question text is
      // withheld until the output guard clears it).
      onProgress: (chars: number) => void
      // Terminal: the guarded question (`text`) or, if the guard tripped, a `fallbackKind`.
      onDone: (result: { text: string | null; model: string | null; fallbackKind: SafetyKind | null }) => void
      onError: (error: Error) => void
    }
  ) {
    const controller = new AbortController()
    const run = async () => {
      let resultText: string | null = null
      let resultModel: string | null = null
      let fallbackKind: SafetyKind | null = null
      try {
        const response = await fetch(`${getBackendBaseUrl()}/generate-question`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: controller.signal,
          credentials: "include",
        })

        if (!response.ok || !response.body) {
          throw new Error(`Unable to stream question (${response.status})`)
        }

        const decoder = new TextDecoder()
        const reader = response.body.getReader()
        let buffer = ""

        // Parse one SSE event chunk (the text between blank lines). Returns true when
        // the stream is finished ([DONE]). Throws on a server-sent error payload.
        const processEvent = (eventChunk: string): boolean => {
          for (const line of eventChunk.split(/\r?\n/)) {
            const trimmed = line.trim()
            if (!trimmed.startsWith("data:")) continue
            const data = trimmed.slice(5).trim()
            if (!data) continue
            if (data === "[DONE]") return true
            let parsed: { progress?: number; text?: string; model?: string; fallback?: string; error?: string }
            try {
              parsed = JSON.parse(data)
            } catch {
              continue // ignore a rare malformed JSON fragment
            }
            if (parsed.error) throw new Error(parsed.error)
            if (typeof parsed.progress === "number") handlers.onProgress(parsed.progress)
            if (typeof parsed.text === "string") resultText = parsed.text
            if (typeof parsed.model === "string") resultModel = parsed.model
            if (parsed.fallback) fallbackKind = parsed.fallback as SafetyKind
          }
          return false
        }

        const done = () => handlers.onDone({ text: resultText, model: resultModel, fallbackKind })

        while (true) {
          const { value, done: streamDone } = await reader.read()
          if (streamDone) break
          buffer += decoder.decode(value, { stream: true })
          const events = buffer.split(/\r?\n\r?\n/)
          buffer = events.pop() ?? ""
          for (const evt of events) {
            if (processEvent(evt)) {
              done()
              return
            }
          }
        }

        if (buffer.trim() && processEvent(buffer)) {
          done()
          return
        }

        done()
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          handlers.onError(new Error("Question generation timed out. Check whether Ollama is running."))
          return
        }
        handlers.onError(error instanceof Error ? error : new Error("Unknown stream error"))
      }
    }

    void run()
    return () => controller.abort()
  },
}
