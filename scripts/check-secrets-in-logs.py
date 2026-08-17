"""Check production backend logs for secret leakage.

Reads the gitignored deploy/.env.production, extracts secret values, and
searches the backend container logs for each. Prints only PASS/FAIL per
secret NAME (never the value), so secrets never appear in output.
"""
import re
import subprocess
import sys
from pathlib import Path

ENV_FILE = Path("deploy/.env.production")
SECRET_KEYS = [
    "POSTGRES_PASSWORD",
    "AUTH_JWT_SECRET",
    "GROQ_API_KEY",
    "TAVILY_API_KEY",
    "GOOGLE_API_KEY",
]

if not ENV_FILE.exists():
    print("deploy/.env.production not found — nothing to check")
    sys.exit(0)

env = {}
for line in ENV_FILE.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")

values = {k: v for k, v in env.items() if k in SECRET_KEYS and v}
if not values:
    print("no secret values found in env file")
    sys.exit(0)

cmd = [
    "docker", "compose", "-p", "insightforge-prod",
    "logs", "--no-color", "backend",
]
logs = subprocess.run(cmd, capture_output=True, text=True).stdout

failures = []
for key, value in values.items():
    found = value in logs
    print(f"[{'FAIL' if found else 'PASS'}] {key} not in logs")
    if found:
        failures.append(key)

print("RESULT:", "NO SECRETS FOUND IN LOGS" if not failures else f"LEAK DETECTED: {failures}")
sys.exit(1 if failures else 0)
