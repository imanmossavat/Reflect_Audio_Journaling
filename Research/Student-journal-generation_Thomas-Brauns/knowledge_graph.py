"""
knowledge_graph.py — World State → Knowledge Graph
====================================================
Converts the world_state.json produced by stage_01 into a queryable
directed graph using networkx.

This module is imported by two pipeline stages:

  1. stage_03_repair.py     — GraphValidator replaces the LLM repair pass
                               with deterministic structural checks.
  2. stage_02_event_timeline.py — build_timeline_skeletons() runs a biased
                               random walk that decides WHAT the next event
                               is about, so the LLM only has to write the text.

It is not a pipeline stage itself and has no "output" file. Running it
directly (`python knowledge_graph.py`) inspects an existing world_state.json
and prints a graph summary — useful for debugging.

Requirements:
  pip install networkx
"""

import json
import random
from datetime import datetime, timedelta

import networkx as nx

import config


# ─────────────────────────────────────────────────────────────────────────────
# 1. LOADING — world_state.json → nx.DiGraph
# ─────────────────────────────────────────────────────────────────────────────

def load_graph(world_state: dict) -> nx.DiGraph:
    """
    Convert a world_state dict (from stage_01) into a directed graph.

    Node types:
      - entity  : person, place, project, object, organization, habit
      - arc     : story arc node (so events can point at arcs directly)
      - project : project node

    Edge types (stored as edge attribute 'rel'):
      - latent_fact relations  : "works_at", "avoids", "owes_money_to", ...
      - arc membership         : entity → arc  (rel="involved_in")
      - project membership     : entity → project (rel="related_to")
    """
    G = nx.DiGraph()

    # ── Entity nodes ──────────────────────────────────────────────────────────
    for entity in world_state.get("entities", []):
        G.add_node(
            entity["id"],
            node_type="entity",
            name=entity.get("name", ""),
            type=entity.get("type", ""),
            domains=entity.get("domains", []),
            salience=entity.get("salience", "medium"),
            notes=entity.get("notes", ""),
        )

    # ── Story arc nodes ───────────────────────────────────────────────────────
    for arc in world_state.get("story_arcs", []):
        G.add_node(
            arc["arc_id"],
            node_type="arc",
            title=arc.get("title", ""),
            status=arc.get("status", "active"),
            summary=arc.get("summary", ""),
        )
        # Edges: entity → arc  (rel="involved_in")
        for eid in arc.get("involved_entities", []):
            if eid in G.nodes:
                G.add_edge(eid, arc["arc_id"], rel="involved_in")

    # ── Project nodes ─────────────────────────────────────────────────────────
    for project in world_state.get("projects", []):
        G.add_node(
            project["project_id"],
            node_type="project",
            title=project.get("title", ""),
            status=project.get("status", "active"),
            notes=project.get("notes", ""),
        )
        for eid in project.get("related_entities", []):
            if eid in G.nodes:
                G.add_edge(eid, project["project_id"], rel="related_to")

    # ── Latent fact edges ─────────────────────────────────────────────────────
    for fact in world_state.get("latent_facts", []):
        subj = fact.get("subject")
        obj  = fact.get("object")
        if subj and obj and subj in G.nodes and obj in G.nodes:
            G.add_edge(
                subj,
                obj,
                rel=fact.get("relation", "related_to"),
                arc=fact.get("arc_id"),
                confidence=fact.get("confidence", "assumed"),
                fact_id=fact.get("fact_id"),
            )

    return G


# ─────────────────────────────────────────────────────────────────────────────
# 2. QUERYING — helpers that replace LLM-based consistency checks
# ─────────────────────────────────────────────────────────────────────────────

class GraphValidator:
    """
    Drop-in replacement for the LLM repair pass in stage_03.
    All checks are deterministic — no LLM calls needed.
    """

    def __init__(self, G: nx.DiGraph):
        self.G = G
        self.entity_ids  = {n for n, d in G.nodes(data=True) if d.get("node_type") == "entity"}
        self.arc_ids     = {n for n, d in G.nodes(data=True) if d.get("node_type") == "arc"}
        self.project_ids = {n for n, d in G.nodes(data=True) if d.get("node_type") == "project"}

    # ── Single-event checks ───────────────────────────────────────────────────

    def validate_event(self, event: dict) -> list[str]:
        """
        Check one event against the graph.
        Returns a list of violation strings (empty = clean).
        """
        violations = []
        eid = event.get("event_id", "?")

        # Entity references
        for entity in event.get("involved_entities", []):
            if entity not in self.entity_ids:
                violations.append(f"{eid}: unknown entity '{entity}'")

        # Arc reference
        arc = event.get("story_arc_id")
        if arc and arc not in self.arc_ids:
            violations.append(f"{eid}: unknown arc '{arc}'")

        # Importance range
        imp = event.get("importance")
        if imp is not None:
            try:
                if not (1 <= int(imp) <= 5):
                    violations.append(f"{eid}: importance {imp} out of range 1–5")
            except (ValueError, TypeError):
                violations.append(f"{eid}: importance '{imp}' is not a number")

        return violations

    def repair_event(self, event: dict) -> tuple[dict, list[str]]:
        """
        Minimal-edit repair: fix only what is provably wrong.
        Returns (repaired_event, repair_log).
        Messiness in text is preserved — only structural fields are touched.
        """
        e = event.copy()
        log = []
        eid = event.get("event_id", "?")

        # Strip unknown entities
        original = e.get("involved_entities", [])
        clean    = [x for x in original if x in self.entity_ids]
        removed  = set(original) - set(clean)
        if removed:
            log.append(f"{eid}: removed unknown entities {removed}")
        e["involved_entities"] = clean

        # Null invalid arc (leave remapping to the prompt, or drop it)
        arc = e.get("story_arc_id")
        if arc and arc not in self.arc_ids:
            log.append(f"{eid}: nulled unknown arc '{arc}'")
            e["story_arc_id"] = None

        # Clamp importance
        imp = e.get("importance")
        if imp is not None:
            try:
                clamped = max(1, min(5, int(imp)))
                if clamped != imp:
                    log.append(f"{eid}: clamped importance {imp} → {clamped}")
                e["importance"] = clamped
            except (ValueError, TypeError):
                e["importance"] = 3
                log.append(f"{eid}: replaced invalid importance with 3")

        return e, log

    # ── Batch validation ──────────────────────────────────────────────────────

    def validate_timeline(self, events: list[dict]) -> list[str]:
        """Validate all events and also check timestamp ordering."""
        all_violations = []
        seen_ids = set()
        prev_ts  = ""

        for event in events:
            eid = event.get("event_id", "?")

            if eid in seen_ids:
                all_violations.append(f"Duplicate event_id: '{eid}'")
            seen_ids.add(eid)

            ts = event.get("timestamp", "")
            if ts and prev_ts and ts < prev_ts:
                all_violations.append(f"{eid}: timestamp out of order ({ts} after {prev_ts})")
            if ts:
                prev_ts = ts

            all_violations.extend(self.validate_event(event))

        return all_violations

    # ── Graph queries (what an LLM previously had to guess at) ───────────────

    def entities_in_arc(self, arc_id: str) -> list[str]:
        """All entity IDs connected to a given arc."""
        return [
            n for n in self.G.predecessors(arc_id)
            if self.G.nodes[n].get("node_type") == "entity"
        ]

    def arcs_for_entity(self, entity_id: str) -> list[str]:
        """All arc IDs that a given entity is involved in."""
        return [
            n for n in self.G.successors(entity_id)
            if self.G.nodes[n].get("node_type") == "arc"
        ]

    def unresolved_arcs(self) -> list[str]:
        """Arc IDs whose status is active or stalled."""
        return [
            n for n, d in self.G.nodes(data=True)
            if d.get("node_type") == "arc"
            and d.get("status") in ("active", "stalled")
        ]

    def entities_by_salience(self, level: str) -> list[str]:
        """Entity IDs filtered by salience: 'low' | 'medium' | 'high'."""
        return [
            n for n, d in self.G.nodes(data=True)
            if d.get("node_type") == "entity" and d.get("salience") == level
        ]

    def shared_entities(self, arc_a: str, arc_b: str) -> list[str]:
        """Entities that appear in both arc_a and arc_b — useful for cross-arc events."""
        a = set(self.entities_in_arc(arc_a))
        b = set(self.entities_in_arc(arc_b))
        return list(a & b)


# ─────────────────────────────────────────────────────────────────────────────
# 3. TRAJECTORY SAMPLER — graph-driven event selection for stage_02
# ─────────────────────────────────────────────────────────────────────────────

def sample_next_event(
    G: nx.DiGraph,
    last_visited: dict,        # {node_id: datetime}
    current_time: datetime,
    unresolved_arcs: set,
) -> dict:
    """
    Pick the next node to generate an event about.

    Scoring (higher = more likely to be picked next):
      +3.0  node is linked to an unresolved arc
      +0–2  recency decay (not visited recently → score rises)
      +0.1  per graph edge (highly connected nodes stay salient)

    Returns a skeleton dict that you pass to the LLM.
    The LLM only writes the 'text' field — structure comes from here.
    """
    candidates = []

    for node_id, data in G.nodes(data=True):
        if data.get("node_type") != "entity":
            continue  # only pick entity nodes as event subjects

        score = 0.0

        # Boost if connected to an unresolved arc
        for successor in G.successors(node_id):
            if successor in unresolved_arcs:
                score += 3.0
                break

        # Recency decay: nodes dormant for longer bubble back up
        last = last_visited.get(node_id)
        if last:
            days_since = (current_time - last).days
            score += min(days_since * 0.3, 2.0)
        else:
            score += 2.0  # never visited = high priority

        # Connectivity bonus
        score += G.degree(node_id) * 0.1

        candidates.append((node_id, score))

    if not candidates:
        raise ValueError("No entity nodes found in graph.")

    # Weighted random — not pure random, not fully deterministic
    total = sum(s for _, s in candidates)
    r = random.uniform(0, total)
    cumulative = 0.0
    for node_id, score in candidates:
        cumulative += score
        if r <= cumulative:
            selected = node_id
            break
    else:
        selected = candidates[-1][0]

    return _build_event_skeleton(selected, G, current_time)


def _build_event_skeleton(node_id: str, G: nx.DiGraph, timestamp: datetime) -> dict:
    """
    Build the structured event skeleton before the LLM sees it.
    The LLM fills in 'text' only — not story_arc_id, not involved_entities.
    """
    node = G.nodes[node_id]

    # Find the most relevant arc for this entity
    arcs = [
        n for n in G.successors(node_id)
        if G.nodes[n].get("node_type") == "arc"
    ]
    arc_id = arcs[0] if arcs else None

    # Nearby entities (direct graph neighbours, up to 3)
    neighbours = [
        n for n in G.neighbors(node_id)
        if G.nodes[n].get("node_type") == "entity"
    ][:3]

    return {
        "event_id":         f"E_{timestamp.strftime('%Y%m%d%H%M')}",
        "timestamp":        timestamp.isoformat(),
        "primary_entity":   node_id,
        "story_arc_id":     arc_id,
        "involved_entities": [node_id] + neighbours,
        "text":             None,   # LLM fills this in
        "latent_fact_updates": [],  # LLM fills this in
        "importance":       None,   # LLM fills this in
    }


def build_timeline_skeletons(
    G: nx.DiGraph,
    start_date: datetime,
    duration_days: int = 30,
    events_per_day: float = 0.8,   # average — actual count varies
) -> list[dict]:
    """
    Generate a full list of event skeletons for the LLM to flesh out.
    Replaces the monolithic 'generate 90 days of events' prompt.

    Each skeleton has all structural fields pre-filled.
    The LLM only writes natural-language text per event.
    """
    validator     = GraphValidator(G)
    unresolved    = set(validator.unresolved_arcs())
    last_visited  = {}
    skeletons     = []
    current_time  = start_date

    total_events = int(duration_days * events_per_day)

    for _ in range(total_events):
        skeleton = sample_next_event(G, last_visited, current_time, unresolved)
        skeletons.append(skeleton)

        # Mark this node as visited
        last_visited[skeleton["primary_entity"]] = current_time

        # Advance time: 0.5–3 hours between events, occasional day gaps
        gap_hours = random.choices(
            [random.uniform(0.5, 3), random.uniform(18, 30)],
            weights=[0.75, 0.25]
        )[0]
        current_time += timedelta(hours=gap_hours)

    return skeletons


# ─────────────────────────────────────────────────────────────────────────────
# 4. GRAPH SUMMARY — human-readable inspection
# ─────────────────────────────────────────────────────────────────────────────

def print_graph_summary(G: nx.DiGraph) -> None:
    entities  = [(n, d) for n, d in G.nodes(data=True) if d.get("node_type") == "entity"]
    arcs      = [(n, d) for n, d in G.nodes(data=True) if d.get("node_type") == "arc"]
    projects  = [(n, d) for n, d in G.nodes(data=True) if d.get("node_type") == "project"]

    print("\n── Knowledge Graph Summary ──────────────────────────")
    print(f"  Nodes  : {G.number_of_nodes()}")
    print(f"  Edges  : {G.number_of_edges()}")
    print(f"  Entity nodes  : {len(entities)}")
    print(f"  Arc nodes     : {len(arcs)}")
    print(f"  Project nodes : {len(projects)}")

    print("\n  Entities by salience:")
    for level in ("high", "medium", "low"):
        names = [d.get("name", n) for n, d in entities if d.get("salience") == level]
        if names:
            print(f"    {level:6s}: {', '.join(names)}")

    print("\n  Story arcs:")
    for arc_id, data in arcs:
        status = data.get("status", "?")
        title  = data.get("title", arc_id)
        degree = G.in_degree(arc_id)
        print(f"    [{status:10s}] {arc_id}  —  {title}  ({degree} entities)")

    print("\n  Most connected entities (top 5):")
    by_degree = sorted(entities, key=lambda x: G.degree(x[0]), reverse=True)[:5]
    for node_id, data in by_degree:
        print(f"    {data.get('name', node_id):20s}  degree={G.degree(node_id)}")

    print("─────────────────────────────────────────────────────\n")


# ─────────────────────────────────────────────────────────────────────────────
# 5. MAIN — inspect the graph built from data/world_state.json
# ─────────────────────────────────────────────────────────────────────────────

def main():
    world_state_path = config.PATHS["world_state"]

    if not world_state_path.exists():
        print(f"No world state found at {world_state_path}.")
        print("Run stage_01_world_state.py first, then re-run this script.")
        return

    print(f"Loading world state from {world_state_path}...")
    with open(world_state_path, encoding="utf-8") as f:
        world_state = json.load(f)

    G = load_graph(world_state)
    print_graph_summary(G)

    # Show validator in action if a repaired event stream already exists
    repaired_path = config.PATHS["events_repaired"]
    if repaired_path.exists():
        print("Validating events_repaired.json against the graph...")
        with open(repaired_path, encoding="utf-8") as f:
            events_data = json.load(f)
        events = events_data.get("events", [])

        validator  = GraphValidator(G)
        violations = validator.validate_timeline(events)

        if violations:
            print(f"\n⚠️  {len(violations)} violation(s) found:")
            for v in violations[:15]:
                print(f"   - {v}")
            if len(violations) > 15:
                print(f"   ... and {len(violations) - 15} more")
        else:
            print("✓  All events are consistent with the knowledge graph.")
    else:
        print("(Skipping event validation — events_repaired.json not found)")

    # Demo: generate a handful of sample skeletons via the biased random walk
    print("\nGenerating 5 sample event skeletons via biased random walk...")
    start_date = datetime.fromisoformat(config.START_DATE).replace(hour=9)
    skeletons = build_timeline_skeletons(
        G,
        start_date=start_date,
        duration_days=5,
        events_per_day=1.0,
    )
    for s in skeletons:
        entity_name = G.nodes[s["primary_entity"]].get("name", s["primary_entity"])
        arc_title = (
            G.nodes[s["story_arc_id"]].get("title", s["story_arc_id"])
            if s["story_arc_id"] and s["story_arc_id"] in G.nodes else "—"
        )
        neighbours = [G.nodes[n].get("name", n) for n in s["involved_entities"][1:]]
        print(f"  {s['timestamp'][:16]}  entity={entity_name:20s}  arc={arc_title}")
        if neighbours:
            print(f"  {'':16s}  also involves: {', '.join(neighbours)}")

    print("\nDone. Import knowledge_graph.py in your stage files to use these tools.")


if __name__ == "__main__":
    main()