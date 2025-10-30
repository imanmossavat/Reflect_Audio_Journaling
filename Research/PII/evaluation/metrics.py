def compute_metrics(results):
    """Compute precision, recall, F1, and return detailed summary + micro/macro scores."""
    summary = {}
    micro_tp = micro_fp = micro_fn = 0

    # per-label stats
    for lbl, s in results.items():
        tp, fn, fp = s["correct"], s["missed"], s["wrong"]

        precision = tp / (tp + fp) if (tp + fp) else 0
        recall = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

        summary[lbl] = {
            **s,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
        }

        micro_tp += tp
        micro_fp += fp
        micro_fn += fn

    # macro averages
    if summary:
        macro_p = sum(s["precision"] for s in summary.values()) / len(summary)
        macro_r = sum(s["recall"] for s in summary.values()) / len(summary)
        macro_f1 = sum(s["f1"] for s in summary.values()) / len(summary)
    else:
        macro_p = macro_r = macro_f1 = 0

    # micro averages
    micro_p = micro_tp / (micro_tp + micro_fp) if (micro_tp + micro_fp) else 0
    micro_r = micro_tp / (micro_tp + micro_fn) if (micro_tp + micro_fn) else 0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) else 0

    totals = {
        "macro": {"precision": macro_p, "recall": macro_r, "f1": macro_f1},
        "micro": {"precision": micro_p, "recall": micro_r, "f1": micro_f1},
    }

    return summary, totals


def print_metrics(summary, totals):
    """Pretty-print evaluation metrics."""
    print("\n--- Evaluation Summary (filtered) ---")
    for lbl, s in summary.items():
        print(
            f"{lbl:<12} "
            f"Correct:{s['correct']:4d}  Missed:{s['missed']:4d}  Wrong:{s['wrong']:4d}  "
            f"P:{s['precision']:.3f}  R:{s['recall']:.3f}  F1:{s['f1']:.3f}"
        )

    print("\n--- Macro Averages ---")
    print(f"P:{totals['macro']['precision']:.3f}  R:{totals['macro']['recall']:.3f}  F1:{totals['macro']['f1']:.3f}")

    print("\n--- Micro Averages ---")
    print(f"P:{totals['micro']['precision']:.3f}  R:{totals['micro']['recall']:.3f}  F1:{totals['micro']['f1']:.3f}")
