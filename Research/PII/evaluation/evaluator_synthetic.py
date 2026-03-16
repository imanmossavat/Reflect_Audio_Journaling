import json
from collections import defaultdict
from sklearn.metrics import precision_score, recall_score, f1_score


# ---------------------------------------------------------
# Utilities
# ---------------------------------------------------------

def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def findings_to_tuples(findings):
    """
    Convert PiiFinding objects into (start, end, label) tuples.
    """
    return [(f.start_char, f.end_char, f.label) for f in findings]


def overlaps(g, p):
    """
    Soft match: spans overlap AND labels match.
    """
    gs, ge, gl = g
    ps, pe, pl = p

    if gl != pl:
        return False
    return not (ge <= ps or pe <= gs)


# ---------------------------------------------------------
# Main evaluation function
# ---------------------------------------------------------

def evaluate(detector, dataset, debug=False):
    y_true = []
    y_pred = []

    per_label_true = defaultdict(list)
    per_label_pred = defaultdict(list)

    per_label_fp = defaultdict(int)
    per_label_fn = defaultdict(int)
    per_label_tp = defaultdict(int)

    # NEW: confusion matrix and label tracker
    confusion = defaultdict(lambda: defaultdict(int))
    labels_set = set()

    for i, sample in enumerate(dataset):
        text = sample["text"]
        gold = [(e["start"], e["end"], e["label"]) for e in sample["entities"]]
        pred = findings_to_tuples(detector.detect(text))

        if debug:
            print("\n======================")
            print(f"TEXT #{i+1}")
            print(text)
            print("----------------------")
            print("GOLD:", gold)
            print("PRED:", pred)

        # register labels
        for g in gold:
            labels_set.add(g[2])
        for p in pred:
            labels_set.add(p[2])

        # FN + TP
        for g in gold:
            matched = any(overlaps(g, p) for p in pred)

            # NEW: detect label mismatches when overlaps occur
            for p in pred:
                if overlaps(g, p) and g[2] != p[2]:
                    confusion[g[2]][p[2]] += 1
                    if debug:
                        print(f"❗ LABEL MISMATCH: gold={g} pred={p}")

            y_true.append(1)
            y_pred.append(1 if matched else 0)

            per_label_true[g[2]].append(1)
            per_label_pred[g[2]].append(1 if matched else 0)

            # Count FN / TP
            if matched:
                per_label_tp[g[2]] += 1
                if debug:
                    print(f"✔ TP  {g}   -> CORRECT")
            else:
                per_label_fn[g[2]] += 1
                confusion[g[2]]["NONE"] += 1
                if debug:
                    print(f"❌ FN  {g}   -> MISSED")

        # FP
        for p in pred:
            if not any(overlaps(g, p) for g in gold):
                y_true.append(0)
                y_pred.append(1)

                per_label_true[p[2]].append(0)
                per_label_pred[p[2]].append(1)

                per_label_fp[p[2]] += 1
                confusion["NONE"][p[2]] += 1

                if debug:
                    print(f"❌ FP  {p}   -> WRONG EXTRA DETECTION")

    # global metrics
    micro_precision = precision_score(y_true, y_pred, zero_division=0)
    micro_recall = recall_score(y_true, y_pred, zero_division=0)
    micro_f1 = f1_score(y_true, y_pred, zero_division=0)

    # per-label metrics
    per_label_scores = {}
    for label in per_label_true:
        p = precision_score(per_label_true[label], per_label_pred[label], zero_division=0)
        r = recall_score(per_label_true[label], per_label_pred[label], zero_division=0)
        f = f1_score(per_label_true[label], per_label_pred[label], zero_division=0)
        per_label_scores[label] = {
            "precision": p,
            "recall": r,
            "f1": f,
            "tp": per_label_tp[label],
            "fp": per_label_fp[label],
            "fn": per_label_fn[label],
        }

    if debug:
        print("\n===== FINAL METRICS =====")
        print("PRECISION:", micro_precision)
        print("RECALL:", micro_recall)
        print("F1:", micro_f1)
        print("\nPER LABEL SCORES:")
        for k,v in per_label_scores.items():
            print(k, v)
        print("\nCONFUSION MATRIX RAW:", dict(confusion))
        print("LABELS FOUND:", labels_set)

    return micro_precision, micro_recall, micro_f1, per_label_scores, confusion, labels_set
