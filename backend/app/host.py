"""Run both HTTP services on one container host with a private ADK loopback port."""

import os
import signal
import subprocess
import sys
import time

from app.config import settings


def main():
    if (
        not settings.adk_service_token
        or not settings.model_key(settings.adk_model)
        or not settings.model_key(settings.crew_model)
    ):
        raise SystemExit(
            "Set ADK_SERVICE_TOKEN and the selected model credentials before starting the host"
        )
    if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
        # Only the public API receives the private research service binding.
        entry = "app.main:app" if settings.research_service_url else "app.adk_service.server:adk_app"
        os.execv(sys.executable, [sys.executable, "-m", "uvicorn", entry, "--host", "0.0.0.0", "--port", os.getenv("PORT", "80")])
    processes = []

    def stop(*_):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    try:
        for entry, host, port in [
            ("app.adk_service.server:adk_app", "127.0.0.1", "8001"),
            ("app.main:app", "0.0.0.0", os.getenv("PORT", "8000")),
        ]:
            processes.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        entry,
                        "--host",
                        host,
                        "--port",
                        port,
                    ]
                )
            )
        while all(proc.poll() is None for proc in processes):
            time.sleep(0.5)
        raise SystemExit("A TRIPPY service exited")
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


if __name__ == "__main__":
    main()
