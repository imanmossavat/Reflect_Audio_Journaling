from llama_index.llms.ollama import Ollama
import pandas as pd, os, json

OLLAMA_BASE_URL = "http://localhost:11434"
MODELS_TO_TEST  = ["mistral", "qwen3.5:4b", "llama3"]
RESULTS_PATH    = "./eval_results"

# ── your actual REFLECT prompt ────────────────────────────────────────────────
# paste your real /generate-question template here
REFLECT_PROMPT = """You are a reflective journaling assistant.
Given the following journal entry, generate a single clarifying question
that helps the writer go deeper on something they mentioned but didn't explore.

Rules:
- Ask about ONE specific thing from the entry
- Do not ask yes/no questions
- Do not start with "How does that make you feel"
- Keep it under 20 words

Journal entry:
{journal_text}

Question:"""

# ── test entries ──────────────────────────────────────────────────────────────
TEST_ENTRIES = {
    "venting":    open("eval_data/e01.txt").read(),
    "flat_day":   open("eval_data/e04.txt").read(),
    "structured": open("eval_data/e06.txt").read(),
    "reflective": open("eval_data/e10.txt").read(),
    "gratitude":  open("eval_data/e13.txt").read(),
}

# ── judge prompt ──────────────────────────────────────────────────────────────
JUDGE_PROMPT = """Rate this journaling question on 3 dimensions.
Respond only with valid JSON, no other text.

Journal entry:
{journal_text}

Generated question:
{question}

Rate each dimension 1-5:
- specificity: does it reference something concrete from the entry (not generic)?
- depth: would it push the writer to reflect meaningfully?
- rule_following: does it follow the rules (not yes/no, not "how does that make you feel", under 20 words)?

{{"specificity": N, "depth": N, "rule_following": N, "reason": "one sentence"}}"""

def generate_question(llm, journal_text: str) -> str:
    prompt = REFLECT_PROMPT.format(journal_text=journal_text)
    return str(llm.complete(prompt)).strip()

def judge_question(judge_llm, journal_text: str, question: str) -> dict:
    prompt = JUDGE_PROMPT.format(journal_text=journal_text, question=question)
    raw = str(judge_llm.complete(prompt)).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        try:
            return json.loads(raw[start:end]) if start != -1 else {}
        except json.JSONDecodeError:
            return {}

# ── main ──────────────────────────────────────────────────────────────────────
os.makedirs(RESULTS_PATH, exist_ok=True)

# judge is fixed to mistral to avoid self-grading bias
judge_llm = Ollama(model="mistral", base_url=OLLAMA_BASE_URL, request_timeout=120.0)

rows = []

for model_name in MODELS_TO_TEST:
    print(f"\n── {model_name} ──")
    llm = Ollama(model=model_name, base_url=OLLAMA_BASE_URL, request_timeout=120.0)

    for entry_type, journal_text in TEST_ENTRIES.items():
        question = generate_question(llm, journal_text)
        scores   = judge_question(judge_llm, journal_text, question)
        print(f"  [{entry_type}] {question}")

        rows.append({
            "model":          model_name,
            "entry_type":     entry_type,
            "question":       question,
            "specificity":    scores.get("specificity"),
            "depth":          scores.get("depth"),
            "rule_following": scores.get("rule_following"),
            "reason":         scores.get("reason"),
        })

df = pd.DataFrame(rows)

summary = df.groupby("model")[["specificity", "depth", "rule_following"]].mean().round(2)
print("\n── prompt following summary ──")
print(summary)

df.to_csv(f"{RESULTS_PATH}/prompt_eval.csv", index=False)
summary.to_csv(f"{RESULTS_PATH}/prompt_eval_summary.csv")