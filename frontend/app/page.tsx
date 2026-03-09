'use client'

import { useState, useRef, ChangeEvent, FormEvent, ReactNode, JSX } from "react";

const API = "http://localhost:8000";

type Stage = "upload" | "choose" | "segment-select" | "question";
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

interface Segment {
  name: string;
  summary: string;
  startIndex: number;
  endIndex: number;
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
  const [topic, setTopic] = useState<string>("");
  const [step, setStep] = useState<number>(1);
  const [question, setQuestion] = useState<string>("");
  const [answer, setAnswer] = useState<string>("");
  const [history, setHistory] = useState<QAEntry[]>([]);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [selectedSegment, setSelectedSegment] = useState<number | null>(null);
  const [renamingSegment, setRenamingSegment] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState<string>("");
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

      // Fetch segments
      const segRes = await fetch(`${API}/segment`, { method: "POST" });
      if (segRes.ok) {
        const segs = await segRes.json();
        setSegments(segs);
      }

      setStage("choose");
    } catch (err) {
      const error = err instanceof Error ? err.message : "Unknown error";
      setError(error);
    } finally {
      setLoading(false);
    }
  }

  async function generate(currentStep: number, currentMode: Mode = mode, textOverride?: string): Promise<void> {
    setLoading(true);
    setQuestion("");
    setError("");
    try {
      const res = await fetch(`${API}/generate-question`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: currentMode,
          step: currentMode === "deep_dive" ? currentStep : null,
          topic: topic || null,
          history: history,
          text_override: textOverride || null,
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
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const payload = line.slice(6);
            if (payload === "[DONE]") break;
            try {
              const { token } = JSON.parse(payload);
              setQuestion((q) => q + token);
            } catch { }
          }
        }
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
    if (m === "clarifying") generate(0, m);
  }

  function handleAnswerAndContinue(): void {
    if (answer.trim()) {
      const timestamp = new Date().toISOString();
      setHistory([...history, { timestamp, question, answer }]);
      setAnswer("");
    }
    if (mode === "clarifying") {
      generate(0, "clarifying");
    } else if (mode === "deep_dive") {
      const textOverride = selectedSegment !== null ? segments[selectedSegment].name + "\n" + segments[selectedSegment].summary : undefined;
      generate(step, "deep_dive", textOverride);
    }
  }

  function handleNextStep(): void {
    if (answer.trim()) {
      const timestamp = new Date().toISOString();
      setHistory([...history, { timestamp, question, answer }]);
      setAnswer("");
    }
    const next = step + 1;
    setStep(next);
    const textOverride = selectedSegment !== null ? segments[selectedSegment].name + "\n" + segments[selectedSegment].summary : undefined;
    generate(next, "deep_dive", textOverride);
  }

  function goBackToModes(): void {
    setStage("choose");
    setMode(null);
    setQuestion("");
    setAnswer("");
    setError("");
  }

  function startDeepDive(): void {
    if (segments.length > 0) {
      setStage("segment-select");
    } else {
      setStep(1);
      generate(1, "deep_dive");
    }
  }

  function selectSegmentAndDive(segmentIndex: number): void {
    setSelectedSegment(segmentIndex);
    const segment = segments[segmentIndex];
    const segmentText = segment ? segment.name + "\n" + segment.summary : "";
    setStep(1);
    generate(1, "deep_dive", segmentText);
  }

  function startRenamingSegment(index: number): void {
    setRenamingSegment(index);
    setRenameValue(segments[index].name);
  }

  function finishRenamingSegment(index: number, newName: string): void {
    if (newName.trim()) {
      const updated = [...segments];
      updated[index].name = newName.trim();
      setSegments(updated);
    }
    setRenamingSegment(null);
    setRenameValue("");
  }

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
                    onClick={() => setMode("deep_dive")}>deep dive</button>
                </div>
                {mode === "deep_dive" && (
                  <div className="flex gap-3">
                    <input className="flex-1 bg-[#443737] border border-[#2e2e2e] rounded-sm text-[#e8e0d4] px-3 py-2 text-sm font-serif outline-none focus:border-[#444] transition-colors"
                      placeholder="topic (optional)" value={topic} onChange={(e) => setTopic(e.target.value)} onKeyDown={(e) => e.key === "Enter" && startDeepDive()} />
                    <button className="bg-transparent border border-[#3a3a3a] rounded-sm text-[#c8b89a] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#c8b89a] transition-colors"
                      onClick={startDeepDive}>start</button>
                  </div>
                )}
              </div>
            )}

            {/* Select Segment for Deep Dive */}
            {stage === "segment-select" && (
              <div className="flex flex-col gap-5">
                <p className="text-xs tracking-wide text-[#999]">which segment would you like to explore?</p>
                <div className="flex flex-col gap-3">
                  {segments.map((segment, idx) => (
                    <div
                      key={idx}
                      className={`p-4 rounded border cursor-pointer transition-colors ${
                        selectedSegment === idx
                          ? "border-[#c8b89a] bg-[#1a1a1a]"
                          : "border-[#2a2a2a] hover:border-[#3a3a3a]"
                      }`}
                      onClick={() => selectSegmentAndDive(idx)}
                    >
                      {renamingSegment === idx ? (
                        <input
                          autoFocus
                          type="text"
                          value={renameValue}
                          onChange={(e) => setRenameValue(e.target.value)}
                          onBlur={() => finishRenamingSegment(idx, renameValue)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") finishRenamingSegment(idx, renameValue);
                            if (e.key === "Escape") setRenamingSegment(null);
                          }}
                          className="w-full bg-[#0e0e0e] border border-[#3a3a3a] rounded px-2 py-1 text-[#e8e0d4] text-sm outline-none"
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <div
                          onClick={(e) => {
                            e.stopPropagation();
                            startRenamingSegment(idx);
                          }}
                          className="hover:text-[#c8b89a] transition-colors"
                        >
                          <p className="font-semibold text-[#e8e0d4] text-sm">{segment.name}</p>
                          <p className="text-[#888] text-xs mt-1">{segment.summary}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <button
                  className="bg-transparent border border-[#555] rounded-sm text-[#999] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#777] hover:text-[#ccc] transition-colors"
                  onClick={goBackToModes}
                >
                  back to modes
                </button>
              </div>
            )}

            {/* Question */}
            {stage === "question" && (
              <div className="flex flex-col gap-5">
                {mode === "deep_dive" && (
                  <div className="flex gap-1.5 items-center">
                    {STEPS.map((st) => (
                      <div key={st.n} title={st.label} className={`w-1.5 h-1.5 rounded-full transition-colors duration-300 ${st.n === step ? "bg-[#c8b89a]" : st.n < step ? "bg-[#4a4a4a]" : "bg-[#2e2e2e]"}`} />
                    ))}
                  </div>
                )}
                <p className="text-base leading-relaxed text-[#e8e0d4] min-h-16">{question || "..."}</p>
                <textarea
                  className="w-full bg-[#0e0e0e] border border-[#2e2e2e] rounded-sm text-[#e8e0d4] px-3 py-2 text-sm font-serif outline-none focus:border-[#444] transition-colors resize-none"
                  placeholder="Your answer..."
                  rows={4}
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                />
                <div className="flex gap-3 flex-wrap">
                  {mode === "clarifying" && (
                    <button className="bg-transparent border border-[#3a3a3a] rounded-sm text-[#c8b89a] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#c8b89a] transition-colors"
                      onClick={handleAnswerAndContinue}>next question</button>
                  )}
                  {mode === "deep_dive" && (
                    <>
                      <button className="bg-transparent border border-[#3a3a3a] rounded-sm text-[#c8b89a] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#c8b89a] transition-colors"
                        onClick={handleAnswerAndContinue}>ask another</button>
                      {step < 6 && (
                        <button className="bg-transparent border border-[#3a3a3a] rounded-sm text-[#c8b89a] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#c8b89a] transition-colors"
                          onClick={handleNextStep}>next step →</button>
                      )}
                    </>
                  )}
                  <button className="bg-transparent border border-[#555] rounded-sm text-[#999] px-4 py-2 text-xs tracking-wider cursor-pointer hover:border-[#777] hover:text-[#ccc] transition-colors"
                    onClick={goBackToModes}>back to modes</button>
                </div>
              </div>
            )}

            {error && <p className="mt-4 text-xs text-[#a05050]">{error}</p>}
          </>
        )}

        {error && <p className="mt-4 text-xs text-[#a05050]">{error}</p>}
      </div>
    </main>
  );
}
