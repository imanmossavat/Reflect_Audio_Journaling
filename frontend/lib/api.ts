export type SourceStatus = "processed" | "not processed" | string

export interface SourceRecord {
  id: number
  filename: string | null
  file_type: string | null
  text: string | null
  status: SourceStatus
  created_at: string
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
  return (process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "")
}

function withTimeout(timeoutMs: number): { signal: AbortSignal; cancel: () => void } {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  return {
    signal: controller.signal,
    cancel: () => clearTimeout(timeoutId),
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const timeout = withTimeout(20000)
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
  uploadTextSource(sourceText: string, processed = false) {
    const body = new FormData()
    body.append("source_text", sourceText)
    return request<SourceRecord>(processed ? "/source/uploadText/processed" : "/source/uploadText/raw", {
      method: "POST",
      body,
    })
  },
  uploadFileSource(file: File, processed = false) {
    const body = new FormData()
    body.append("file", file)
    return request<SourceRecord>(processed ? "/source/uploadFile/processed" : "/source/uploadFile/raw", {
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
  patchSourceText(sourceId: number, text: string) {
    return request<SourceRecord>(`/source/${sourceId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })
  },
  processSource(sourceId: number) {
    return request<SourceRecord>(`/source/process/${sourceId}`, { method: "POST" })
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

        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const events = buffer.split("\n\n")
          buffer = events.pop() ?? ""

          for (const evt of events) {
            if (!evt.startsWith("data:")) continue
            const payloadText = evt.replace(/^data:\s*/, "").trim()
            if (payloadText === "[DONE]") {
              handlers.onDone()
              return
            }
            try {
              const parsed = JSON.parse(payloadText) as { token?: string }
              if (parsed.token) handlers.onToken(parsed.token)
            } catch {
              // Ignore malformed chunks while streaming.
            }
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
