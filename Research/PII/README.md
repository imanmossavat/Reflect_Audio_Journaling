# PII Detection Research

This folder contains research and evaluation code for detecting
Personally Identifiable Information (PII) in journal transcripts.

The work in this folder focuses on **privacy-preserving text analysis**
for personal journaling data and directly informs the PII detection
component used in the REFLECT backend.

## Research goals
- Explore feasibility of local PII detection
- Compare rule-based and model-based approaches
- Measure precision, recall, and error types
- Understand trade-offs between false positives and false negatives

## Approach
A **hybrid detection strategy** is explored:
- Pattern-based detection (regex)
- Named Entity Recognition (NER)
- Label normalization and filtering
- Quantitative evaluation using annotated datasets

All code in this folder is research-oriented and not production-hardened.

## Folder structure

- `classes/`  
  Core data structures used throughout the PII pipeline.

- `data/`  
  Datasets and label definitions used for training and evaluation.

- `models/`  
  Model loading and abstraction logic.

- `patterns/`  
  Regex-based PII detection patterns.

- `structures/`  
  Typed representations of detected PII spans.

- `evaluation/`  
  Evaluation pipeline, metrics, and dataset comparisons.

- `*.ipynb`  
  Exploratory notebooks for analysis and model comparison.

## Datasets
Evaluation is performed on:
- Synthetic journaling data
- Public PII datasets (e.g. ai4privacy/pii-masking-200k)

Labels are normalized to a reduced set relevant for journaling contexts
(e.g. PERSON, ORG, GPE, EMAIL).

## Status
- Research and evaluation only
- Findings informed backend PII design
- Kept for traceability and reproducibility
