"""Serialize Ollama generation across the whole backend.

Even though the chat/route handlers are now non-blocking (they offload the
synchronous Ollama work so the event loop stays free), we still only want *one*
generation hitting the model at a time — running two heavy generations in
parallel would compete for the same model/VRAM and degrade both.

`generation_lock` is a process-wide semaphore. Acquire it with `async with` around
any call that makes Ollama generate. Extra requests queue on the semaphore (FIFO)
and run as soon as the model is free; they are never rejected. Retrieval and
embedding calls deliberately stay *outside* the gate so search remains responsive
while an answer is being written.

To allow N concurrent generations later (paired with `OLLAMA_NUM_PARALLEL` on the
Ollama server), raise the semaphore size below — it is the single knob.
"""

import asyncio

# Size 1 = one generation at a time.
_MAX_CONCURRENT_GENERATIONS = 1

generation_lock = asyncio.Semaphore(_MAX_CONCURRENT_GENERATIONS)


def is_busy() -> bool:
    """True if a generation is currently holding the gate.

    Used to tell an incoming request it will have to wait, so the UI can show a
    "queued" state instead of an unexplained pause.
    """
    return generation_lock.locked()
