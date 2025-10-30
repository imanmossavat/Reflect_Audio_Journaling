from collections import defaultdict

def evaluate_dataset(dataset, detector, label_map, relevant_labels, limit=1000):
    """
    Evaluate a PII detector against a dataset.

    Args:
        dataset: Hugging Face dataset (ai4privacy/pii-masking-200k)
        detector: instance of PIIDetector
        label_map: dict mapping dataset labels -> detector labels
        relevant_labels: set of labels to consider
        limit (int): number of examples to check

    Returns:
        results: dict[label -> {correct, missed, wrong}]
        examples: dict of example tuples (correct/missed/wrong)
    """
    results = defaultdict(lambda: {"correct": 0, "missed": 0, "wrong": 0})
    examples = {"correct": [], "missed": [], "wrong": []}

    for example in dataset.select(range(limit)):
        text = example["source_text"]
        gold_spans = example["privacy_mask"]
        detected = detector.detect(text)

        # Normalize gold spans
        gold = []
        for gs in gold_spans:
            lbl = gs.get("label")
            mapped = label_map.get(lbl)
            if mapped in relevant_labels:
                gold.append((gs["start"], gs["end"], mapped, text[gs["start"]:gs["end"]]))

        if not gold:
            continue

        # True positives and misses
        for start, end, label, snippet in gold:
            found = any(
                d.label == label and d.start_char < end and d.end_char > start
                for d in detected
            )
            if found:
                results[label]["correct"] += 1
                examples["correct"].append((label, snippet))
            else:
                results[label]["missed"] += 1
                examples["missed"].append((label, snippet))

        # False positives
        for d in detected:
            if d.label not in relevant_labels:
                continue
            overlap = any(
                d.start_char < end and d.end_char > start and d.label == label
                for start, end, label, _ in gold
            )
            if not overlap:
                results[d.label]["wrong"] += 1
                examples["wrong"].append((d.label, getattr(d, "preview", "")))

    return results, examples