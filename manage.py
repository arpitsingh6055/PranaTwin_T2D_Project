"""Cross-platform project commands; run with your activated environment."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(args, cwd=ROOT):
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["setup", "up", "test", "evaluate", "build", "smoke", "down"]
    )
    args = parser.parse_args()
    pnpm = shutil.which("pnpm.cmd" if os.name == "nt" else "pnpm")
    if args.command in ("setup", "build", "test", "smoke") and not pnpm:
        parser.error("Install Node.js 24 and pnpm 11, and ensure pnpm is on PATH.")
    if args.command == "setup":
        run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        run([pnpm, "install", "--frozen-lockfile"], ROOT / "frontend")
        run([pnpm, "build"], ROOT / "frontend")
    elif args.command == "build":
        run([pnpm, "build"], ROOT / "frontend")
    elif args.command == "up":
        if not (ROOT / "frontend/dist/index.html").exists():
            parser.error("Run setup or build first")
        run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "engine.api:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--no-access-log",
            ]
        )
    elif args.command == "evaluate":
        run([sys.executable, "-m", "engine.evaluate"])
    elif args.command == "test":
        run([sys.executable, "-m", "ruff", "check", "engine", "tests", "--select", "F"])
        run([sys.executable, "-m", "pytest", "-q", "--basetemp=.test-tmp"])
        for task in ("typecheck", "lint", "test"):
            run([pnpm, task], ROOT / "frontend")
    elif args.command == "smoke":
        run([pnpm, "smoke"], ROOT / "frontend")
    elif args.command == "down":
        print(
            "For native up, press Ctrl+C in its terminal. For containers: docker compose down. No unrelated process is terminated."
        )


if __name__ == "__main__":
    main()
