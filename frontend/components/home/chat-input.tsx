"use client"

import { Mic, MessageCircle, Sparkles, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { CurrentQuestion, QuestionType } from "./types"

interface ChatInputProps {
  currentQuestion: CurrentQuestion | null
  inputValue: string
  setInputValue: (v: string) => void
  isGeneratingQuestion: boolean
  onSubmitText: (e: React.FormEvent) => Promise<void>
  onSelectQuestionType: (type: QuestionType) => Promise<void>
}

export function ChatInput({
  currentQuestion,
  inputValue,
  setInputValue,
  isGeneratingQuestion,
  onSubmitText,
  onSelectQuestionType,
}: ChatInputProps) {
  return (
    <div className="border-t bg-background p-4">
      <div className="max-w-2xl mx-auto">
        {currentQuestion &&
          currentQuestion.type !== "quantitative" &&
          currentQuestion.content.trim().length > 0 &&
          !isGeneratingQuestion && (
            <form onSubmit={onSubmitText} className="flex gap-2 mb-4">
              <div className="flex-1 relative">
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Write your response..."
                  className="w-full min-h-15 p-3 pr-10 rounded-xl border bg-background resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                  rows={2}
                />
                <button
                  type="button"
                  className="absolute bottom-2 right-2 p-1.5 rounded-lg hover:bg-muted text-muted-foreground"
                >
                  <Mic className="h-4 w-4" />
                </button>
              </div>
              <Button
                type="submit"
                disabled={!inputValue.trim()}
                className="bg-emerald-600 hover:bg-emerald-700 text-white self-end"
              >
                <Send className="h-4 w-4" />
              </Button>
            </form>
          )}

        {!currentQuestion && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground text-center">What would you like to add?</p>
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => void onSelectQuestionType("clarifying")}
                disabled={isGeneratingQuestion}
                className="p-3 rounded-xl border-2 border-border hover:border-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors text-left"
              >
                <MessageCircle className="h-4 w-4 text-amber-600 mb-2" />
                <div className="text-sm font-medium">Clarifying</div>
                <div className="text-xs text-muted-foreground">
                  {isGeneratingQuestion ? "Generating..." : "Follow-up questions"}
                </div>
              </button>
              <button
                onClick={() => void onSelectQuestionType("guided")}
                disabled={isGeneratingQuestion}
                className="p-3 rounded-xl border-2 border-border hover:border-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors text-left"
              >
                <Sparkles className="h-4 w-4 text-emerald-600 mb-2" />
                <div className="text-sm font-medium">Guided</div>
                <div className="text-xs text-muted-foreground">
                  {isGeneratingQuestion ? "Generating..." : "Reflective prompts"}
                </div>
              </button>
              <button
                onClick={() => void onSelectQuestionType("quantitative")}
                disabled={isGeneratingQuestion}
                className="p-3 rounded-xl border-2 border-border hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors text-left"
              >
                <span className="text-blue-600 font-bold text-xs block mb-2">1-10</span>
                <div className="text-sm font-medium">Quantitative</div>
                <div className="text-xs text-muted-foreground">Rate how you feel</div>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
