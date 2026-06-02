export type SourceStatus =
  | "processed"
  | "not processed"
  | "queued"
  | "transcribing"
  | "chunking"
  | "indexing"
  | "failed"
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
  status: SourceStatus
  created_at: string
}

export interface SourceTag {
  id: number
  name: string
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
  created_at: string
}

export type ChatStreamStageName = "searching" | "retrieved" | "thinking" | "writing"

export interface ChatStreamHandlers {
  onStage: (stage: { name: ChatStreamStageName; count?: number }) => void
  onThinking: (delta: string) => void
  onToken: (delta: string) => void
  onSources?: (sources: QuerySource[]) => void
  onDone: (info: { model: string | null; message_id: number }) => void
  onError: (error: Error) => void
}

export interface ChatSummary {
  id: number
  title: string
  source_id: number | null
  message_count: number
  edited_at: string
  created_at: string
}

export interface ChatDetail {
  id: number
  title: string
  source_id: number | null
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
}

type GenerateQuestionMode = "clarifying" | "deep_dive"

export interface GenerateQuestionRequest {
  mode: GenerateQuestionMode
  step?: number
  focus_tag?: string
  focus_tag_summary?: string
  history?: Array<Record<string, unknown>>
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

function extractEventPayloads(rawEvent: string): string[] {
  const lines = rawEvent.replace(/\r\n/g, "\n").split("\n")
  const payloads: string[] = []

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue

    if (trimmed.startsWith("data:")) {
      payloads.push(trimmed.slice(5).trimStart())
      continue
    }

    // Be tolerant of occasional missing first character in streamed chunks.
    if (trimmed.startsWith("ata:")) {
      payloads.push(trimmed.slice(4).trimStart())
      continue
    }

    if (trimmed.startsWith("{") || trimmed === "[DONE]") {
      payloads.push(trimmed)
    }
  }

  return payloads
}

function extractTokensFromAnyText(text: string): string[] {
  const tokens: string[] = []
  const tokenPattern = /"token"\s*:\s*"((?:\\.|[^"\\])*)"/g
  let match: RegExpExecArray | null

  while ((match = tokenPattern.exec(text)) !== null) {
    try {
      tokens.push(JSON.parse(`"${match[1]}"`))
    } catch {
      tokens.push(match[1].replace(/\\"/g, '"').replace(/\\\\/g, "\\"))
    }
  }

  return tokens
}

function parseNestedTokenPayload(text: string): { tokens: string[]; done: boolean } {
  const normalized = text
    .replace(/\\r\\n/g, "\n")
    .replace(/\\n/g, "\n")
    .replace(/\r\n/g, "\n")

  const nestedEvents = normalized.split(/\n\n+/)
  const tokens: string[] = []
  let done = false

  for (const nestedEvent of nestedEvents) {
    const payloads = extractEventPayloads(nestedEvent)
    for (const payload of payloads) {
      const trimmed = payload.trim()
      if (!trimmed) continue
      if (trimmed === "[DONE]") {
        done = true
        continue
      }

      try {
        const parsed = JSON.parse(trimmed) as { token?: string }
        if (typeof parsed.token === "string" && parsed.token.length > 0) {
          tokens.push(parsed.token)
        }
      } catch {
        const fallbackTokens = extractTokensFromAnyText(trimmed)
        tokens.push(...fallbackTokens)
      }
    }

    if (payloads.length === 0) {
      const fallbackTokens = extractTokensFromAnyText(nestedEvent)
      tokens.push(...fallbackTokens)
      if (nestedEvent.includes("[DONE]")) {
        done = true
      }
    }
  }

  return { tokens, done }
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
  patchSource(sourceId: number, fields: { text?: string; text_html?: string; filename?: string; created_at?: string }) {
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
            case "thinking":
              if (typeof parsed.delta === "string") handlers.onThinking(parsed.delta)
              break
            case "token":
              if (typeof parsed.delta === "string") handlers.onToken(parsed.delta)
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
            case "error":
              handlers.onError(new Error((parsed.detail as string) || "Stream error"))
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
      onToken: (token: string) => void
      onDone: () => void
      onError: (error: Error) => void
    }
  ) {
    const controller = new AbortController()
    const run = async () => {
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
        let fullStreamText = ""
        let emittedTokenCount = 0

        const emitToken = (token: string) => {
          if (!token) return
          handlers.onToken(token)
          emittedTokenCount += 1
        }

        const processPayload = (payloadText: string): boolean => {
          const trimmedPayload = payloadText.trim()
          if (!trimmedPayload) return false

          if (trimmedPayload === "[DONE]") {
            return true
          }

          try {
            const parsed = JSON.parse(trimmedPayload) as { token?: string }
            if (typeof parsed.token === "string" && parsed.token.length > 0) {
              const nested = parseNestedTokenPayload(parsed.token)
              if (nested.tokens.length > 0 && (parsed.token.includes("data:") || parsed.token.includes("ata:") || parsed.token.includes("\"token\""))) {
                for (const nestedToken of nested.tokens) {
                  emitToken(nestedToken)
                }
              } else {
                emitToken(parsed.token)
              }

              if (nested.done) {
                return true
              }
            }
          } catch {
            const nested = parseNestedTokenPayload(trimmedPayload)
            for (const nestedToken of nested.tokens) {
              emitToken(nestedToken)
            }
            if (nested.done || trimmedPayload.includes("[DONE]")) {
              return true
            }
          }

          return false
        }

        const processEventChunk = (eventChunk: string): boolean => {
          const payloads = extractEventPayloads(eventChunk)
          if (payloads.length === 0) {
            const fallbackTokens = extractTokensFromAnyText(eventChunk)
            for (const token of fallbackTokens) {
              emitToken(token)
            }
            return eventChunk.includes("[DONE]")
          }

          for (const payload of payloads) {
            if (processPayload(payload)) {
              return true
            }
          }

          return false
        }

        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          const decoded = decoder.decode(value, { stream: true })
          fullStreamText += decoded
          buffer += decoded
          const events = buffer.split(/\r?\n\r?\n/)
          buffer = events.pop() ?? ""

          for (const evt of events) {
            if (processEventChunk(evt)) {
              handlers.onDone()
              return
            }
          }
        }

        if (buffer.trim()) {
          if (processEventChunk(buffer)) {
            handlers.onDone()
            return
          }
        }

        if (emittedTokenCount === 0) {
          const fallbackTokens = extractTokensFromAnyText(fullStreamText)
          for (const token of fallbackTokens) {
            emitToken(token)
          }
        }

        handlers.onDone()
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
