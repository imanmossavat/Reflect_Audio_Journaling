"""
run_pipeline.py — Sequential pipeline runner
===============================================
Runs all 5 pipeline stages in order, one after another, without requiring
anyone to stay at the keyboard. Intended for long, unattended runs (e.g. a
90-day simulation on a 70B model, which can take hours).

Each stage is run as a subprocess. If a stage fails, the runner stops
immediately and prints which stage failed and why — it does not continue
to the next stage with broken or missing input data.

A full log of stdout/stderr from every stage is written to
pipeline_run.log in the project root, in addition to being printed live
to the console. This means you can walk away and check the log later
instead of having to watch the terminal the whole time.

Usage:
    python run_pipeline.py

To run only a subset of stages (e.g. to resume after a fix), edit the
STAGES list below and comment out the ones you don't want to re-run.
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

STAGES = [
    "stage_01_world_state.py",
    "stage_02_event_timeline.py",
    "stage_03_repair.py",
    "stage_04_note_generation.py",
    "stage_05_qa_generation.py",
]

LOG_FILE = Path("pipeline_run.log")


def log_line(text: str, log_handle) -> None:
    """Print to console and write to the log file simultaneously."""
    print(text)
    log_handle.write(text + "\n")
    log_handle.flush()


def run_stage(script: str, log_handle) -> bool:
    """
    Run one stage as a subprocess, streaming its output live.
    Returns True if the stage exited successfully, False otherwise.
    """
    log_line(f"\n{'=' * 70}", log_handle)
    log_line(f"  STARTING: {script}   ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})", log_handle)
    log_line(f"{'=' * 70}\n", log_handle)

    start = time.time()

    process = subprocess.Popen(
        [sys.executable, script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    for line in process.stdout:
        log_line(line.rstrip(), log_handle)

    process.wait()
    elapsed = time.time() - start
    minutes = elapsed / 60

    if process.returncode == 0:
        log_line(f"\n✓ {script} completed in {minutes:.1f} minutes.\n", log_handle)
        return True
    else:
        log_line(
            f"\n✗ {script} FAILED (exit code {process.returncode}) "
            f"after {minutes:.1f} minutes.\n",
            log_handle,
        )
        return False


def main() -> None:
    overall_start = time.time()

    with open(LOG_FILE, "w", encoding="utf-8") as log_handle:
        log_line(f"Pipeline run started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", log_handle)
        log_line(f"Stages to run: {len(STAGES)}", log_handle)
        log_line(f"Full log: {LOG_FILE.resolve()}", log_handle)

        for script in STAGES:
            if not Path(script).exists():
                log_line(f"\n✗ Cannot find '{script}' in the current directory. Stopping.", log_handle)
                sys.exit(1)

            success = run_stage(script, log_handle)
            if not success:
                log_line(
                    f"\nPipeline stopped at '{script}'. "
                    f"Check the output above (and {LOG_FILE}) for the error, fix it, "
                    f"then re-run this script. Earlier stages do not need to be repeated "
                    f"as long as their output files in data/ are still present.",
                    log_handle,
                )
                sys.exit(1)

        total_minutes = (time.time() - overall_start) / 60
        log_line(f"\n{'=' * 70}", log_handle)
        log_line(f"  ALL STAGES COMPLETE — total time: {total_minutes:.1f} minutes", log_handle)
        log_line(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", log_handle)
        log_line(f"{'=' * 70}", log_handle)
        log_line("\nOutputs are in the data/ directory:", log_handle)
        log_line("  data/world_state.json", log_handle)
        log_line("  data/events_raw.json", log_handle)
        log_line("  data/events_repaired.json", log_handle)
        log_line("  data/notes.json", log_handle)
        log_line("  data/qa_pairs.json", log_handle)


if __name__ == "__main__":
    main()
