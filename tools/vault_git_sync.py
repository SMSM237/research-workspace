"""One bounded Git sync for an existing Obsidian Vault.

Run this from a local scheduler. Keep Obsidian Git automatic timers disabled so
two clients do not mutate the same checkout concurrently. Conflicts stop the
run and retain both Git histories for manual resolution.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


def git(vault: Path, *args: str, accept: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    result = subprocess.run(
        ["git", "-C", str(vault), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=90,
        env=env,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if result.returncode not in accept:
        detail = (result.stderr or result.stdout).strip()[-1000:]
        raise RuntimeError(f"Git {args[0]} failed ({result.returncode}): {detail}")
    return result


def lock_file(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        handle.write(b"0") if path.stat().st_size == 0 else None
        handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            handle.close()
            return None
    else:
        import fcntl

        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return None
    return handle


def unlock_file(handle):
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    handle.close()


def save_status(path: Path, status: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as stream:
        json.dump(status, stream, ensure_ascii=False, indent=2)
        staged = Path(stream.name)
    os.replace(staged, path)


def sync(vault: Path, branch: str, expected_remote: str) -> dict[str, object]:
    actual_root = Path(git(vault, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if os.path.normcase(str(actual_root)) != os.path.normcase(str(vault.resolve())):
        raise RuntimeError("The selected folder is not the repository root")
    actual_branch = git(vault, "symbolic-ref", "--short", "HEAD").stdout.strip()
    if actual_branch != branch:
        raise RuntimeError(f"Expected branch {branch}, found {actual_branch}")
    remote = git(vault, "remote", "get-url", "origin").stdout.strip()
    if remote != expected_remote:
        raise RuntimeError("Origin does not match the configured private Vault repository")
    if git(vault, "ls-files", "-u").stdout:
        raise RuntimeError("Unresolved Git conflict; no automatic commit or push attempted")

    git(vault, "add", "-A")
    staged = git(vault, "diff", "--cached", "--quiet", accept=(0, 1)).returncode == 1
    if staged:
        stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        git(vault, "commit", "-m", f"vault sync: {stamp}")

    git(vault, "fetch", "origin", branch)
    git(vault, "merge", "--no-edit", f"origin/{branch}")
    git(vault, "push", "origin", branch)
    local = git(vault, "rev-parse", "HEAD").stdout.strip()
    remote_head = git(vault, "ls-remote", "origin", f"refs/heads/{branch}").stdout.split()[0]
    if local != remote_head:
        raise RuntimeError("Push returned without matching the remote branch")
    remaining = git(vault, "status", "--porcelain", "-z").stdout
    return {"result": "synced", "head": local, "committed": staged, "pending_changes": bool(remaining)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--expected-remote", required=True)
    parser.add_argument("--branch", default="main")
    args = parser.parse_args()
    handle = lock_file(args.state_dir / "run.lock")
    if handle is None:
        return 0  # A previous run is still active; never overlap Git operations.
    try:
        try:
            result = sync(args.vault, args.branch, args.expected_remote)
            code = 0
        except (OSError, subprocess.TimeoutExpired, RuntimeError, IndexError) as error:
            result = {"result": "blocked", "error": str(error)[-1000:]}
            code = 1
        result["checked_at"] = datetime.now(timezone.utc).isoformat()
        save_status(args.state_dir / "status.json", result)
        if sys.stdout is not None:
            print(json.dumps(result, ensure_ascii=False))
        return code
    finally:
        unlock_file(handle)


if __name__ == "__main__":
    sys.exit(main())
