export interface RawSource {
  id: string
  type: "recording" | "file" | "text"
  name: string
  content?: string
  duration?: string
  createdAt: string
  timestamp: string
  included: boolean
  tags: { name: string; color: string }[]
  status: string
}

export type AddSourceMode = null | "recording" | "file" | "text" | "phone"
export type LeftTab = "sources" | "chats"
