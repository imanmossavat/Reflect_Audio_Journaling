"use client";

/* ──────────────────────────────────────────────────────────────────────────
   Reflect product tour — spotlight + coach-marks over your real workspace.

   How it works: each step optionally names a `target`. The tour finds the
   matching element via [data-tour="<target>"], reads its bounding box, and
   draws a spotlight + a tooltip beside it. Steps with target:null show a
   centered welcome / finish card.

   Zero dependencies beyond React. Drop this file in (e.g. components/Tour.tsx),
   import "./tour.css" once, tag your elements with data-tour, and mount it.
   ────────────────────────────────────────────────────────────────────────── */

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

export type TourStep = {
  /** matches an element with data-tour="<target>"; null = centered card */
  target: string | null;
  eyebrow: string;
  title: string;
  body: string;
};

export const TOUR_STEPS: TourStep[] = [
  { target: null, eyebrow: "Welcome in", title: "This is your Reflect workspace.", body: "Everything lives on one screen: your library on the left, a conversation in the middle, tools on the right. Here's a 40-second tour of what you can do." },
  { target: "new", eyebrow: "Capture", title: "Add anything you want to reflect on.", body: "Hit New to record a voice note, upload an audio file or transcript, jot a quick note, or send a recording straight from your phone. Each one becomes a \u201Csource.\u201D" },
  { target: "library", eyebrow: "Library", title: "Your sources collect here.", body: "Recordings, notes and files stack up in one place. New audio is transcribed locally and shows a live progress state while it processes, and nothing leaves your machine." },
  { target: "tags", eyebrow: "Organize", title: "Tag and filter by theme.", body: "Give sources tags like \u201Cmentor\u201D or \u201Cstress,\u201D then type tag: in the filter to pull up everything on a theme at once, handy when patterns span several weeks." },
  { target: "include", eyebrow: "Context", title: "Choose what the AI reads.", body: "Tick a source to include it. Only included sources are used when you chat or search, so you control exactly what Reflect reasons over." },
  { target: "chat", eyebrow: "Chat", title: "Ask questions across your journal.", body: "Type a question, or tap a suggested prompt, and Reflect answers from your own words, citing your included sources. It runs entirely on a local model." },
  { target: "reflect", eyebrow: "Go deeper", title: "Run a guided reflection.", body: "Start the Gibbs cycle to be walked through a structured reflection: description, feelings, evaluation, analysis, conclusion and an action plan, one stage at a time." },
  { target: "tools", eyebrow: "Tools", title: "Export, search & explore.", body: "Export your reflection to Markdown, ask a quick question across included sources, or open the Graph to see how your tags and sources connect." },
  { target: null, eyebrow: "You're ready", title: "Start with one source.", body: "Add a voice note or a few lines about your week, and Reflect takes it from there. You can replay this tour anytime from the workspace." },
];

const TIP_W = 332;

type Box = { top: number; left: number; width: number; height: number };
type TipPos = { top: number; left: number; center: boolean };

export default function Tour({
  steps = TOUR_STEPS,
  onClose,
}: {
  steps?: TourStep[];
  onClose: () => void;
}) {
  const [i, setI] = useState(0);
  const [rect, setRect] = useState<Box | null>(null);
  const [tip, setTip] = useState<TipPos>({ top: 0, left: 0, center: true });
  const tipRef = useRef<HTMLDivElement | null>(null);
  const step = steps[i];
  const isLast = i === steps.length - 1;

  const measure = useCallback(() => {
    const s = steps[i];
    if (!s.target) {
      setRect(null);
      setTip((t) => ({ ...t, center: true }));
      return;
    }
    const el = document.querySelector<HTMLElement>(`[data-tour="${s.target}"]`);
    if (!el) {
      setRect(null);
      return;
    }
    const r = el.getBoundingClientRect();
    const pad = 6;
    setRect({ top: r.top - pad, left: r.left - pad, width: r.width + pad * 2, height: r.height + pad * 2 });

    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const tipH = tipRef.current ? tipRef.current.offsetHeight : 220;
    const gap = { right: vw - r.right, left: r.left, bottom: vh - r.bottom, top: r.top };
    let top: number;
    let left: number;
    if (gap.right >= TIP_W + 28) {
      left = r.right + 22;
      top = r.top + r.height / 2 - tipH / 2;
    } else if (gap.left >= TIP_W + 28) {
      left = r.left - TIP_W - 22;
      top = r.top + r.height / 2 - tipH / 2;
    } else if (gap.bottom >= tipH + 28) {
      top = r.bottom + 22;
      left = r.left + r.width / 2 - TIP_W / 2;
    } else {
      top = r.top - tipH - 22;
      left = r.left + r.width / 2 - TIP_W / 2;
    }
    left = Math.max(16, Math.min(left, vw - TIP_W - 16));
    top = Math.max(16, Math.min(top, vh - tipH - 16));
    setTip({ top, left, center: false });
  }, [i, steps]);

  useLayoutEffect(() => {
    // Measure synchronously — rAF is paused in hidden/throttled tabs.
    measure();
    // Delayed re-measures catch late font / transition settle.
    const t1 = setTimeout(measure, 90);
    const t2 = setTimeout(measure, 300);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [measure]);

  useEffect(() => {
    const on = () => measure();
    window.addEventListener("resize", on);
    window.addEventListener("scroll", on, true);
    return () => {
      window.removeEventListener("resize", on);
      window.removeEventListener("scroll", on, true);
    };
  }, [measure]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight" || e.key === "Enter") {
        e.preventDefault();
        if (isLast) onClose();
        else setI((x) => x + 1);
      } else if (e.key === "ArrowLeft") {
        setI((x) => Math.max(0, x - 1));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isLast, onClose]);

  const next = () => (isLast ? onClose() : setI((x) => x + 1));
  const back = () => setI((x) => Math.max(0, x - 1));
  const centered = tip.center || !rect;

  return (
    <div className="tour-layer">
      {rect ? (
        <div
          className="tour-spot"
          style={{ top: rect.top, left: rect.left, width: rect.width, height: rect.height }}
        ></div>
      ) : (
        <div className="tour-dim"></div>
      )}

      <button className="tour-skip" onClick={onClose}>Skip tour</button>

      <div
        ref={tipRef}
        className={"tour-tip" + (centered ? " center" : "")}
        style={centered ? undefined : { top: tip.top, left: tip.left }}
      >
        <div className="tour-eyebrow">{step.eyebrow}</div>
        <h3>{step.title}</h3>
        <p>{step.body}</p>
        <div className="tour-foot">
          <div className="tour-dots">
            {steps.map((_, n) => (
              <span key={n} className={"tour-dot" + (n === i ? " on" : "")}></span>
            ))}
          </div>
          <div className="tour-btns">
            {i > 0 && (
              <button className="tour-btn ghost" onClick={back}>Back</button>
            )}
            <button className="tour-btn primary" onClick={next}>
              {isLast ? "Finish" : "Next"}
              {!isLast && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
