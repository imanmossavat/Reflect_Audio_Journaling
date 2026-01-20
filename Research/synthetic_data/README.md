# Synthetic Data

This folder contains **synthetically generated journaling data**
used for research, testing, and evaluation of the REFLECT system.

All data in this folder is artificial and does not contain real user information.

## Why synthetic data is used
Real journal data is highly sensitive and unsuitable for development and testing.
Synthetic data allows controlled experimentation while preserving privacy.

The datasets in this folder are designed to simulate:
- Realistic journaling language
- Longitudinal behavior across days
- Emotional variation
- Topic recurrence and drift
- Explicit and implicit PII mentions

## Design principles
The synthetic data follows these principles:

- **Persona-driven**  
  Each dataset is generated from predefined personas with consistent traits,
  writing styles, life contexts, and recurring themes.

- **Longitudinal structure**  
  Each persona produces multiple journal entries over time, forming a narrative arc
  rather than isolated texts.

- **Controlled PII injection**  
  Names, locations, organizations, and contact details are intentionally injected
  so that PII detection can be evaluated with known ground truth.

- **Segment-aware generation**  
  Entries may contain multiple thematic segments with associated sentiment labels,
  reflecting how real journals evolve within a single entry.

## Folder structure

- `personas/`  
  Persona definitions used to generate the data (background, themes, style).

- `synthetic_persona_data*`  
  Generated datasets. Each folder represents an iteration of the data generation
  approach.

## Versioned datasets
Each `synthetic_persona_data_v*` folder represents a **refinement** of the generation
pipeline.

Later versions typically improve:
- Linguistic realism
- Topic coherence
- Sentiment consistency
- PII placement and traceability
- Cross-entry continuity

Earlier versions are retained for:
- Comparison
- Evaluation reproducibility
- Traceability of design decisions

The most recent version represents the most stable and realistic dataset.

## Usage
These datasets are used to:
- Evaluate topic segmentation approaches
- Test PII detection and offset accuracy
- Validate sentiment and summary pipelines
- Compare guided vs unguided theme mapping

They are not used directly in production.
