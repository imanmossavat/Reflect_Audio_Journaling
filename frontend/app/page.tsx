'use client'

import { useState, useRef, ChangeEvent, JSX, } from "react";
import { customScrollbar } from '../lib/scrollbar';

const API = "http://localhost:8000";

type Stage = "upload" | "choose" | "topic-select" | "question" | "deep-dive-options";
type Mode = "clarifying" | "deep_dive" | null;

interface Step {
  n: number;
  label: string;
}

interface QAEntry {
  timestamp: string;
  question: string;
  answer: string;
}

interface Topic {
  name: string;
  summary: string;
  quotes: string[];
}

interface GenerateOptions {
  step: number;
  mode?: Mode;
  topicName?: string;
  topicSummary?: string;
  history?: QAEntry[];
}

const STEPS: Step[] = [
  { n: 1, label: "Description" },
  { n: 2, label: "Feelings" },
  { n: 3, label: "Evaluation" },
  { n: 4, label: "Analysis" },
  { n: 5, label: "Conclusion" },
  { n: 6, label: "Action" },
];

export default function Home(): JSX.Element {
  const [stage, setStage] = useState<Stage>("upload");
  const [filename, setFilename] = useState<string>("");
  const [mode, setMode] = useState<Mode>(null);
  const [step, setStep] = useState<number>(1);
  const [deepDiveStep, setDeepDiveStep] = useState<number | null>(null);
  const [question, setQuestion] = useState<string>("");
  const [answer, setAnswer] = useState<string>("");
  const [history, setHistory] = useState<QAEntry[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [journalText, setJournalText] = useState<string>("");
  const [selectedTopic, setSelectedTopic] = useState<number | null>(null);
  const [hoveredTopic, setHoveredTopic] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleUpload(e: ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setLoading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API}/upload`, { method: "POST", body: form });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Something went wrong");
      }
      const data = await res.json();
      setFilename(data.filename);
      setStage("choose");
    } catch (err) {
      const error = err instanceof Error ? err.message : "Unknown error";
      setError(error);
    } finally {
      setLoading(false);
    }
  }

  async function generate({ step, mode: m = mode, topicName, topicSummary, history: historyOverride }: GenerateOptions): Promise<void> {
    setLoading(true);
    setQuestion("");
    setError("");
    try {
      const res = await fetch(`${API}/generate-question`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: m,
          step: m === "deep_dive" ? step : null,
          topic: topicName ?? null,
          topic_summary: topicSummary ?? null,
          history: historyOverride ?? history,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Something went wrong");
      }
      const reader = res.body?.getReader();
      if (!reader) return;
      const decoder = new TextDecoder();
      let buffer = "";
      let streamDone = false;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const payload = line.slice(6);
            if (payload === "[DONE]") {
              streamDone = true;
              break;
            }
            try {
              const { token } = JSON.parse(payload);
              setQuestion((q) => q + token);
            } catch { }
          }
        }
        if (streamDone) break;
      }
      setStage("question");
    } catch (err) {
      const error = err instanceof Error ? err.message : "Unknown error";
      setError(error);
    } finally {
      setLoading(false);
    }
  }

  function handleModeSelect(m: Mode): void {
    setMode(m);
    setAnswer("");
    setQuestion("");
    if (m === "clarifying") generate({ step: 0, mode: m });
  }

  function saveAnswerAndGetHistory(): QAEntry[] {
    if (!answer.trim()) return history;
    const updated = [...history, { timestamp: new Date().toISOString(), question, answer }];
    setHistory(updated);
    setAnswer("");
    return updated;
  }

  function handleSubmitAnswer(): void {
    saveAnswerAndGetHistory();
    if (mode === "deep_dive") {
      setStage("deep-dive-options");
      setQuestion("");
    } else if (mode === "clarifying" && deepDiveStep !== null) {
      setMode("deep_dive");
      setStep(deepDiveStep);
      setStage("deep-dive-options");
      setQuestion("");
    } else {
      goBackToModes();
    }
  }

  function deepDiveAskAnother(): void {
    const topic = selectedTopic !== null ? topics[selectedTopic] : undefined;
    generate({ step, mode: "deep_dive", topicName: topic?.name, topicSummary: topic?.summary, history });
  }

  function deepDiveNextStep(): void {
    const next = step + 1;
    setStep(next);
    const topic = selectedTopic !== null ? topics[selectedTopic] : undefined;
    generate({ step: next, mode: "deep_dive", topicName: topic?.name, topicSummary: topic?.summary, history });
  }

  function startClarifyingDetour(): void {
    setDeepDiveStep(step);
    setMode("clarifying");
    setAnswer("");
    generate({ step: 0, mode: "clarifying", history });
  }

  function goBackToModes(): void {
    setStage("choose");
    setMode(null);
    setQuestion("");
    setAnswer("");
    setDeepDiveStep(null);
    setError("");
  }

  async function startDeepDive(): Promise<void> {
    setLoading(true);
    setError("");
    setMode("deep_dive");
    setTopics([]);
    setSelectedTopic(null);
    setHoveredTopic(null);
    try {
      const res = await fetch(`${API}/topics`, { method: "POST" });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to extract topics");
      }
      const data = await res.json();
      setTopics(data.topics);
      setJournalText(data.journal_text);
      setStage("topic-select");
    } catch (err) {
      const error = err instanceof Error ? err.message : "Unknown error";
      setError(error);
    } finally {
      setLoading(false);
    }
  }

  function selectTopicAndDive(topicIndex: number): void {
    setSelectedTopic(topicIndex);
    setMode("deep_dive");
    const topic = topics[topicIndex];
    setStep(1);
    generate({ step: 1, mode: "deep_dive", topicName: topic.name, topicSummary: topic.summary });
  }

  /** Render journal text with quote highlights for the active (hovered or selected) topic */
  function renderHighlightedText(activeTopic: Topic | null, activeColor: string): JSX.Element {
    if (!activeTopic || activeTopic.quotes.length === 0) {
      return <>{journalText}</>;
    }

    // Find all quote occurrences and build highlight ranges
    const ranges: { start: number; end: number }[] = [];
    for (const quote of activeTopic.quotes) {
      let searchFrom = 0;
      while (searchFrom < journalText.length) {
        const idx = journalText.indexOf(quote, searchFrom);
        if (idx === -1) break;
        ranges.push({ start: idx, end: idx + quote.length });
        searchFrom = idx + 1;
      }
    }

    if (ranges.length === 0) return <>{journalText}</>;

    // Sort and merge overlapping ranges
    ranges.sort((a, b) => a.start - b.start);
    const merged: { start: number; end: number }[] = [ranges[0]];
    for (let i = 1; i < ranges.length; i++) {
      const last = merged[merged.length - 1];
      if (ranges[i].start <= last.end) {
        last.end = Math.max(last.end, ranges[i].end);
      } else {
        merged.push(ranges[i]);
      }
    }

    const parts: JSX.Element[] = [];
    let lastEnd = 0;
    merged.forEach((r, i) => {
      if (r.start > lastEnd) {
        parts.push(<span key={`gap-${i}`}>{journalText.slice(lastEnd, r.start)}</span>);
      }
      parts.push(
        <span
          key={`hl-${i}`}
          className="rounded px-0.5 transition-colors duration-200"
          style={{ backgroundColor: activeColor + "33", borderBottom: `2px solid ${activeColor}` }}
        >
          {journalText.slice(r.start, r.end)}
        </span>
      );
      lastEnd = r.end;
    });
    if (lastEnd < journalText.length) {
      parts.push(<span key="tail">{journalText.slice(lastEnd)}</span>);
    }
    return <>{parts}</>;
  }

  const colors = ["#c8b89a", "#9ab8c8", "#b89ac8", "#9ac8a3", "#c89a9a", "#c8c09a"];
  const activeTopicIndex = hoveredTopic ?? selectedTopic;
  const activeTopic = activeTopicIndex !== null ? topics[activeTopicIndex] : null;
  const activeColor = activeTopicIndex !== null ? colors[activeTopicIndex % colors.length] : "#c8b89a";

  return (
    <main className="min-h-screen flex items-center justify-center bg-[#0e0e0e] p-8 font-serif">
      <div className="w-full max-w-lg bg-[#161616] border border-[#2a2a2a] rounded p-10">

        {/* Header */}
        <div className="flex items-center gap-2 mb-8">
          <span className="text-2xl text-[#c8b89a]">◎</span>
          <h1 className="text-sm font-normal tracking-widest text-[#e8e0d4]">reflect</h1>
        </div>

        {loading ? (
          <div className="flex flex-col items-center gap-3 py-6">
            <div className="w-5 h-5 rounded-full border border-[#999] border-t-transparent animate-spin" />
            <p className="text-xs tracking-widest text-[#999]">thinking</p>
          </div>
        ) : (
          <>
            {/* Upload */}
            {stage === "upload" && (
              <div className="flex flex-col gap-5">
                <p className="text-xs tracking-wide text-[#999]">upload a journal entry to begin</p>
                <label className="flex flex-col items-center justify-center gap-2 border border-dashed border-[#2e2e2e] rounded p-10 cursor-pointer text-[#555] hover:border-[#444] transition-colors">
                  <input ref={fileRef} type="file" accept=".txt" onChange={handleUpload} className="hidden" />
                  <span className="text-2xl text-[#c8b89a]">↑</span>
                  <span className="text-xs">.txt file</span>
                </label>
              </div>
            )}

            {/* Choose mode */}
            {stage === "choose" && (
              <div className="flex flex-col gap-5">
                <p className="text-xs text-[#555]">↳ {filename}</p>
                <p className="text-xs tracking-wide text-[#999]">how do you want to reflect?</p>
                <div className="flex gap-3 flex-wrap">
                  <button className="bg-transparent border border-[#3a3a3a] rounded-sm text-[#c8b89a] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#c8b89a] transition-colors disabled:opacity-40"
                    onClick={() => handleModeSelect("clarifying")}>broad questions</button>
                  <button className="bg-transparent border border-[#3a3a3a] rounded-sm text-[#c8b89a] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#c8b89a] transition-colors disabled:opacity-40"
                    onClick={startDeepDive}>deep dive</button>
                </div>
              </div>
            )}

            {/* Select Topic for Deep Dive */}
            {stage === "topic-select" && (
              <div className="flex flex-col gap-5">
                <p className="text-xs tracking-wide text-[#999]">
                  hover a topic to highlight related passages, click to explore
                </p>

                {/* Topic list */}
                <div className="flex flex-wrap gap-2">
                  {topics.map((topic, idx) => {
                    const color = colors[idx % colors.length];
                    return (
                      <button
                        key={idx}
                        className="text-xs px-3 py-1.5 rounded border cursor-pointer transition-all hover:opacity-80"
                        style={{
                          borderColor: activeTopicIndex === idx ? color : "#3a3a3a",
                          color: color,
                          backgroundColor: activeTopicIndex === idx ? color + "15" : "transparent",
                        }}
                        title={topic.summary}
                        onMouseEnter={() => setHoveredTopic(idx)}
                        onMouseLeave={() => setHoveredTopic(null)}
                        onClick={() => selectTopicAndDive(idx)}
                      >
                        {topic.name}
                      </button>
                    );
                  })}
                </div>

                {/* Active topic summary — always reserve space to prevent layout shift */}
                <p className={`text-xs italic min-h-[2rem] transition-colors duration-200 ${activeTopic ? "text-[#777]" : "text-transparent"}`}>
                  {activeTopic?.summary ?? "\u00A0"}
                </p>

                {/* Journal text with highlighted quotes */}
                <div
                  className={`${customScrollbar} relative max-h-80 overflow-y-auto border border-[#2a2a2a] rounded p-4 text-sm leading-relaxed text-[#999] whitespace-pre-wrap`}
                >
                  {renderHighlightedText(activeTopic, activeColor)}
                </div>

                <div className="flex gap-3 flex-wrap">
                  <button
                    className="bg-transparent border border-[#3a3a3a] rounded-sm text-[#c8b89a] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#c8b89a] transition-colors"
                    onClick={() => { setMode("deep_dive"); setStep(1); generate({ step: 1, mode: "deep_dive" }); }}
                  >
                    skip — explore all
                  </button>
                  <button
                    className="bg-transparent border border-[#555] rounded-sm text-[#999] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#777] hover:text-[#ccc] transition-colors"
                    onClick={goBackToModes}
                  >
                    back to modes
                  </button>
                </div>
              </div>
            )}

            {/* Question */}
            {stage === "question" && (
              <div className="flex flex-col gap-5">
                {mode === "deep_dive" && (
                  <div className="flex justify-between w-full">
                    {STEPS.map((st) => (
                      <div key={st.n} className="flex flex-col items-center gap-1">
                        <div className={`w-2 h-2 rounded-full transition-colors duration-300 ${st.n === step ? "bg-[#c8b89a]" : st.n < step ? "bg-[#555]" : "bg-[#2e2e2e]"}`} />
                        <span className={`text-[10px] tracking-wide transition-colors duration-300 ${st.n === step ? "text-[#c8b89a]" : st.n < step ? "text-[#555]" : "text-[#2e2e2e]"}`}>{st.label.toLowerCase()}</span>
                      </div>
                    ))}
                  </div>
                )}
                {mode === "clarifying" && deepDiveStep !== null && (
                  <p className="text-xs text-[#555]">clarifying detour — will return to step {deepDiveStep}</p>
                )}
                <p className="text-base leading-relaxed text-[#e8e0d4] min-h-16">{question || "..."}</p>
                <textarea
                  className="w-full bg-[#0e0e0e] border border-[#2e2e2e] rounded-sm text-[#e8e0d4] px-3 py-2 text-sm font-serif outline-none focus:border-[#444] transition-colors resize-none"
                  placeholder="Your answer..."
                  rows={4}
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                />
                <button className="bg-transparent border border-[#3a3a3a] rounded-sm text-[#c8b89a] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#c8b89a] transition-colors"
                  onClick={handleSubmitAnswer}>answer</button>
              </div>
            )}

            {/* Deep Dive Options (after answering) */}
            {stage === "deep-dive-options" && (
              <div className="flex flex-col gap-5">
                <div className="flex justify-between w-full">
                  {STEPS.map((st) => (
                    <div key={st.n} className="flex flex-col items-center gap-1">
                      <div className={`w-2 h-2 rounded-full transition-colors duration-300 ${st.n === step ? "bg-[#c8b89a]" : st.n < step ? "bg-[#555]" : "bg-[#2e2e2e]"}`} />
                      <span className={`text-[10px] tracking-wide transition-colors duration-300 ${st.n === step ? "text-[#c8b89a]" : st.n < step ? "text-[#555]" : "text-[#2e2e2e]"}`}>{st.label.toLowerCase()}</span>
                    </div>
                  ))}
                </div>
                <p className="text-xs tracking-wide text-[#999]">what would you like to do next?</p>
                <div className="flex flex-col gap-3">
                  <button className="bg-transparent border border-[#3a3a3a] rounded-sm text-[#c8b89a] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#c8b89a] transition-colors"
                    onClick={deepDiveAskAnother}>ask another — {STEPS[step - 1]?.label.toLowerCase()}</button>
                  {step < 6 && (
                    <button className="bg-transparent border border-[#3a3a3a] rounded-sm text-[#c8b89a] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#c8b89a] transition-colors"
                      onClick={deepDiveNextStep}>next step → {STEPS[step]?.label.toLowerCase()}</button>
                  )}
                  <button className="bg-transparent border border-[#3a3a3a] rounded-sm text-[#c8b89a] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#c8b89a] transition-colors"
                    onClick={startClarifyingDetour}>clarifying question</button>
                  <button className="bg-transparent border border-[#555] rounded-sm text-[#999] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#777] hover:text-[#ccc] transition-colors"
                    onClick={goBackToModes}>back to modes</button>
                </div>
              </div>
            )}

            {error && <p className="mt-4 text-xs text-[#a05050]">{error}</p>}
          </>
        )}

      </div>
    </main>
  );
}
