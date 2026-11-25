"""A cancellable process boundary for blocking CrewAI/provider calls."""

import json
import sys
from pathlib import Path

from .specialists import run_specialists


def main():
    # Do not send framework logs, user prompts or credentials to the response channel.
    result_path = Path(sys.argv[1])
    narrative, events = run_specialists(json.load(sys.stdin))
    result_path.write_text(
        json.dumps(
            {"plan": narrative.model_dump(), "events": [e.model_dump() for e in events]}
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
