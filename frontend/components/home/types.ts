export interface RawSource {
  id: string
  type: "recording" | "file" | "text"
  name: string
  content?: string
  duration?: string
  timestamp: string
  included: boolean
  tags: { name: string; color: string }[]
  status: string
}

export interface CurrentQuestion {
  type: QuestionType
  content: string
  scaleData?: { lowLabel: string; highLabel: string }
}

export type QuestionType = "clarifying" | "guided" | "quantitative"
export type AddSourceMode = null | "recording" | "file" | "text" | "phone"
export type LeftTab = "sources" | "chats"
