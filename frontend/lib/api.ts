export type SourceStatus = "processed" | "not processed" | string

export interface SourceRecord {
  id: number
  filename: string | null
  file_type: string | null
  text: string | null
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
}

export interface SaveAnswerRequest {
  source_id: number
  question_text: string
  answer_text: string
}

type GenerateQuestionMode = "clarifying" | "deep_dive"

export interface GenerateQuestionRequest {
  mode: GenerateQuestionMode
  step?: number
  focus_tag?: string
  focus_tag_summary?: string
  history?: Array<Record<string, unknown>>
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
  getSources() {
    return request<SourceRecord[]>("/sources")
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
  uploadProcessedTextSource(sourceText: string) {
    const body = new FormData()
    body.append("source_text", sourceText)
    return request<SourceRecord>("/source/uploadText/processed", {
      method: "POST",
      body,
    })
  },
  uploadTextSource(sourceText: string, processed = false) {
    if (processed) {
      return this.uploadProcessedTextSource(sourceText)
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
  transcribeSource(sourceId: number) {
    return request<SourceRecord>(`/source/transcribe/${sourceId}`, { method: "POST" }).catch((error) => {
      if (error instanceof Error && error.message.includes("API 501")) {
        throw new Error("Transcription is not available in this environment yet. You can still upload text sources.")
      }
      throw error
    })
  },
  patchSourceText(sourceId: number, text: string) {
    return request<SourceRecord>(`/source/${sourceId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })
  },
  processSource(sourceId: number) {
    return request<SourceRecord>(`/source/process/${sourceId}`, { method: "POST" }, 600000)
  },
  query(question: string, top_k = 5) {
    return request<QueryResponse>("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k }),
    })
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
  getOllamaHealth() {
    return request<unknown>("/ollama-health")
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
