"""A cancellable process boundary for blocking CrewAI/provider calls."""

import json
import sys
import traceback
from pathlib import Path

from .specialists import run_specialists


def main():
    # Do not send framework logs, user prompts or credentials to the response channel.
    result_path = Path(sys.argv[1])
    try:
        narrative, events = run_specialists(json.load(sys.stdin))
    except Exception as exc:
        stack = traceback.extract_tb(exc.__traceback__)[-4:]
        result_path.write_text(json.dumps({"error": getattr(exc, "provider_code", type(exc).__name__), "status": getattr(exc, "status_code", None), "frames": [f"{Path(f.filename).name}:{f.name}:{f.lineno}" for f in stack]}), encoding="utf-8")
        raise
    result_path.write_text(
        json.dumps(
            {"plan": narrative.model_dump(), "events": [e.model_dump() for e in events]}
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
