# Tags — how they work, end to end

> Produced 2026-07-01 from a full-codebase audit (backend + frontend) for
> review. Reflects the code as of this date; re-verify file:line references
> before relying on them if this doc has aged.

## 1. What a tag is — data model

**`Backend/database/models.py`**

- **`Tag`** (`tag` table, L73-82): just `id`, `name` (≤255 chars), `created_at`.
  No color, no category, no hierarchy — a tag is a bare string identity.
- **`SourceTag`** (`source_tag` junction, L10-17): composite PK
  `(source_id, tag_id)`, plus one field that carries real weight:
  **`origin: str`** (`"user"` default, or `"llm"`). This is the whole
  provenance model — it lets a re-extraction wipe and replace only the
  LLM-guessed tags while leaving anything the user typed in by hand
  untouched.
- **`QuestionTag`**: same shape, links tags to reflection `Question` rows.
  No origin field — manual-only there.
- **`Source.derived_meta`** (JSON): also holds
  `{"tags": {"model": ..., "prompt_version": ..., "generated_at": ...}}`
  provenance, the same pattern used for summaries and transcripts.

**Structure verdict**: tags have no visual or structural metadata in the
database at all — no color, no type, no nesting. Color is entirely a
frontend runtime concern (§5). Hierarchical tags are an explicitly
**deferred** design decision, not something currently built (see
`my notes/REFLECT_Design_Document.md` §10, "Hierarchical Tags").

## 2. Generation — two separate pipelines, only one is live

There are **two independent LLM tag-generation paths** that don't share
code or data shape:

### Path A — full extraction (`/extract-tags`), built but unused by the UI

- `Backend/app/routes/query.py:255` → calls
  `tagService.extract_and_store_tags(source_id, origin="llm", replace_existing=True)`.
- Prompt: `Backend/app/prompts/tag_extraction_prompt.py` — asks for 3-6
  tags, each with `{name, summary, quotes}`, where quotes must be **exact,
  character-for-character substrings** of the source text (built for
  highlighting, but nothing currently highlights them).
- Grammar-constrained JSON output via Ollama's `format` parameter,
  temperature 0.
- Auto-clears prior `origin="llm"` tags first, replaces them, preserves
  `origin="user"` ones.
- `Frontend/lib/api.ts:564` has a client function for this (`extractTags`)
  but **no component calls it anywhere** — confirmed by grepping the
  entire `Frontend/` tree for `extractTags`/`extract-tags` outside
  `api.ts`. It's also not part of the automatic ingest pipeline —
  `sourceService._process_source_sync` never imports `tagService`.
  **This entire richer pipeline is currently dead from the user's
  perspective**, reachable only by calling the API directly.

### Path B — suggest-then-confirm, the one actually wired into the UI

- `GET /tags/{source_id}/suggest` → `suggest_tags_via_llm()` — a lighter
  prompt, 3-8 tags with just `{name, reason}`, no quotes/summary, and
  **not persisted** until confirmed.
- User picks which suggestions to keep in the **Enrich Source Modal**
  (`Frontend/components/home/enrich-source-modal.tsx`).
- `POST /tags/{source_id}/suggest/confirm` persists the chosen ones — and
  notably, once confirmed they're stored as **`origin="user"`**, not
  `"llm"`, since the user explicitly approved them.
- Net effect: almost nothing in this app's real tag data ends up
  `origin="llm"` in practice — that value exists in the schema for Path A,
  which nothing currently calls.

### Path C — manual add

- `POST /tags/{source_id}` from the source detail page. Always
  `origin="user"`.

## 3. Storage / persistence

`Backend/app/repositories/tagRepository.py` — all names normalized to
lowercase/trimmed on write (`TagCreate` and `BulkTagConfirm` schemas both
do this). Key functions:

- `get_or_create_tag` — upsert by normalized name.
- `add_tag_to_source(..., origin="user")` — link, no-op if already present.
- `clear_llm_tags_for_source` — the selective wipe used before a Path A
  recompute, preserves manual edits.
- `remove_tag_from_source` — delete a single link.
- `get_sources_by_tags(tag_names, match="any"|"all")` — OR vs AND set
  logic via SQL `GROUP BY`/`HAVING`.

## 4. API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/tags/all` | all tags, flat |
| GET | `/tags/all-with-sources` | tags + which sources carry each |
| GET | `/tags/search?tags=a,b&match=any\|all` | sources matching a tag set |
| GET | `/tags/{source_id}` | tags on one source |
| POST | `/tags/{source_id}` | manual add (`origin=user`) |
| DELETE | `/tags/{source_id}/{tag_id}` | remove |
| GET | `/tags/{source_id}/suggest` | LLM suggestions (not persisted) |
| POST | `/tags/{source_id}/suggest/confirm` | persist chosen suggestions |
| POST | `/extract-tags?source_id=` | Path A full extraction (unused by UI) |

Routes live in `Backend/app/routes/tags.py` (all the `/tags/*` ones) and
`Backend/app/routes/query.py` (`/extract-tags`).

## 5. Frontend — display & management

- **`Frontend/lib/api.ts`**: thin client for all endpoints above.
  `SourceTag = {id, name}` — note **`origin` is not exposed to the
  frontend at all**, so the UI has no way to distinguish an
  LLM-confirmed tag from a hand-typed one even if it wanted to.
- **`Frontend/hooks/useSourceManagement.ts`**: fetches/hydrates tags per
  source; assigns color client-side via a deterministic hash of the tag
  name into a fixed 7-color palette (`getTagColor()`, L41-46). Colors are
  never stored — recomputed from the string every render.
- **Source list** (`Frontend/components/home/source-list-panel.tsx`):
  shows the first 3 tags per row as pills, a `tag:`-prefixed search with
  autocomplete, and a multi-select filter (source must match **all**
  active tag filters — AND logic, computed client-side, independent of
  the backend's `match=any|all` search endpoint).
- **Source detail page** (`Frontend/app/sources/[id]/page.tsx`): add/
  remove tags directly, with duplicate-check normalization.
- **`Frontend/components/graph-view.tsx`**: the one place tags drive
  something beyond filtering — builds a node-link graph where each tag is
  a node (sized by how many sources carry it) and edges connect tags that
  co-occur on the same source.
- **URL state**: tag filters are deep-linkable via `?tag=X&tag=Y` query
  params on the home page.

## 6. Role — what tags actually influence

- **RAG retrieval** (`Backend/app/services/retrieval.py:86-162`) — the one
  place tags have real teeth. `ranked_retrieve(..., tags=[...])` resolves
  tag names to source IDs via `get_sources_by_tags(match="any")`, then
  applies a **hard** Chroma metadata filter (`source_id IN [...]`) and
  explicitly **disables** the soft temporal backfill that normally widens
  a thin result set. Scoping a chat/query by tag is an intentional hard
  boundary, not a ranking nudge — if nothing in the tagged sources
  matches, the result is empty rather than falling back.
- **Chat/reflection scoping is a separate, unrelated system** —
  `Chat.reflection_scope` (`topic`/`items`/`source_ids`) comes from a
  different LLM feature (topic grouping), not from tags.
  `GenerateRequest.focus_tag` / `focus_tag_summary` exist in the schema
  but are never populated by any caller — vestigial fields.
- **Chunking** has no tag awareness at all; chunks only carry `source_id`,
  so tag scoping only ever applies at the source level.
- **No connection** to the `Research/Topic_mapping` work — confirmed via
  grep, zero imports either direction.

## 7. File map

```
Backend/database/models.py                     Tag, SourceTag (origin), QuestionTag
Backend/app/schemas/tagSchemas.py               TagCreate, TagRead, TagSuggestion, BulkTagConfirm
Backend/app/schemas/journalSchemas.py           ExtractedTagSchema (Path A only)
Backend/app/services/tagService.py              extraction + suggestion LLM calls
Backend/app/prompts/tag_extraction_prompt.py    Path A prompt (quotes + summary)
Backend/app/repositories/tagRepository.py       CRUD, origin-aware clear, tag-set queries
Backend/app/routes/tags.py                      CRUD + suggest/confirm endpoints
Backend/app/routes/query.py                     /extract-tags (Path A), tags param on /query*
Backend/app/services/retrieval.py               hard tag-scoped filtering for RAG

Frontend/lib/api.ts                             client for all tag endpoints (incl. unused extractTags)
Frontend/hooks/useSourceManagement.ts           fetch/hydrate + client-side color assignment
Frontend/components/home/source-list-panel.tsx  filter UI, tag pills
Frontend/components/home/enrich-source-modal.tsx  suggest -> confirm flow (the live LLM path)
Frontend/components/graph-view.tsx              tag co-occurrence graph
Frontend/app/sources/[id]/page.tsx              manual add/remove
```

## 8. Open items worth a decision

1. **Path A (`/extract-tags`) has no UI entry point.** Either wire it up
   (e.g. into the ingest pipeline, or as an alternate "deep extract" action
   next to the suggest/confirm flow) or remove it as dead code.
2. **`origin` is tracked but never surfaced.** The data to distinguish
   LLM-suggested-then-confirmed tags from hand-typed ones already exists;
   the frontend just doesn't expose it. Worth deciding whether that
   distinction should be visible (e.g. a small badge) before more tag
   volume accumulates.
3. **Hierarchical tags** are a named-but-deferred design principle (see
   the design document's §10) — flat tags today, nesting intentionally
   not built yet.
