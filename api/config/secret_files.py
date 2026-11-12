"""Read secrets from files, never from the repository.

Docker mounts them under /run/secrets; outside Docker they live in <project>/secrets
(git-ignored). The environment is only a fallback for CI and tests.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def secret_dirs() -> tuple[Path, ...]:
    return (Path(os.getenv("SECRETS_DIR", "/run/secrets")), PROJECT_ROOT / "secrets")


def read_secret(name: str, default: str = "") -> str:
    for directory in secret_dirs():
        path = directory / name
        if path.is_file():
            return path.read_text().strip()
    return os.getenv(name.upper(), default)
