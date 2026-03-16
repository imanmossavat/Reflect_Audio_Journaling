# Guided Topic Mapping

This folder contains research exploring **guided semantic theme mapping**
for journal entries using embedding similarity and a predefined theme set.

Rather than allowing unrestricted topic discovery, this approach constrains
output to a fixed set of high-level themes to improve consistency and
longitudinal analysis across journal entries.

## Motivation
Free topic discovery often produces near-duplicate or fragmented topics
(e.g. "school" vs "schoolwork") when applied to journaling data.

For reflective applications, consistency over time is more valuable than
novel topic labels.

This research investigates whether guided mapping improves:
- Thematic consistency across days
- Long-term pattern recognition
- Human interpretability of journal summaries

## Approach
1. Keywords are extracted per journal entry
2. Embeddings are computed for keywords
3. Embeddings are computed for predefined theme labels
4. Keywords are matched to themes using semantic similarity
5. One or more themes are assigned when similarity exceeds a threshold

Themes are **not exclusive**. Entries may map to multiple themes if relevant.

## Example Output
A journal entry describing:
- sleeping in
- napping
- physical recovery
- post-workout soreness

may all map to the same high-level theme:
`"sleep, rest, and recovery"`

This prevents fragmentation while preserving nuance.

## Relation to other research
- Other folders explore unguided topic segmentation
- This folder focuses on **semantic normalization and consistency**
- The MVP currently uses unguided segmentation per recording

## Status
- Research-only experiment
- Not integrated into production pipeline
- Retained for future exploration of longitudinal journaling patterns
