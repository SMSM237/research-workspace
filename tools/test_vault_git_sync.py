import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from vault_git_sync import git, lock_file, sync, unlock_file


def run(*args):
    return subprocess.run(["git", *map(str, args)], check=True, text=True, capture_output=True).stdout.strip()


class VaultGitSyncTest(unittest.TestCase):
    def test_git_subprocess_never_opens_a_console_on_windows(self):
        completed = subprocess.CompletedProcess(["git"], 0, stdout="", stderr="")
        with patch("vault_git_sync.subprocess.run", return_value=completed) as invoke:
            git(Path("vault"), "status")
        expected = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.assertEqual(invoke.call_args.kwargs["creationflags"], expected)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.remote, self.pc, self.phone = base / "remote.git", base / "pc", base / "phone"
        run("init", "--bare", "--initial-branch=main", self.remote)
        run("clone", self.remote, self.pc)
        for repo in (self.pc,):
            run("-C", repo, "config", "user.name", "Test")
            run("-C", repo, "config", "user.email", "test@example.invalid")
        (self.pc / "Tasks").mkdir()
        (self.pc / "Tasks" / "tasks.md").write_text("- [ ] initial\n", encoding="utf-8")
        run("-C", self.pc, "add", "-A")
        run("-C", self.pc, "commit", "-m", "initial")
        run("-C", self.pc, "push", "origin", "main")
        run("clone", self.remote, self.phone)
        run("-C", self.phone, "config", "user.name", "Test")
        run("-C", self.phone, "config", "user.email", "test@example.invalid")

    def test_push_and_pull_keep_distinct_changes(self):
        file = self.pc / "Tasks" / "tasks.md"
        file.write_text(file.read_text(encoding="utf-8") + "- [ ] pc\n", encoding="utf-8")
        pushed = sync(self.pc, "main", str(self.remote))
        self.assertEqual(pushed["result"], "synced")
        self.assertTrue(pushed["committed"])
        run("-C", self.phone, "pull", "--ff-only")
        other = self.phone / "Meetings" / "schedule.md"
        other.parent.mkdir()
        other.write_text("meeting\n", encoding="utf-8")
        run("-C", self.phone, "add", "-A")
        run("-C", self.phone, "commit", "-m", "phone meeting")
        run("-C", self.phone, "push", "origin", "main")
        pulled = sync(self.pc, "main", str(self.remote))
        self.assertEqual(pulled["result"], "synced")
        self.assertFalse(pulled["committed"])
        self.assertEqual((self.pc / "Meetings" / "schedule.md").read_text(encoding="utf-8"), "meeting\n")
        self.assertIn("pc", file.read_text(encoding="utf-8"))

    def test_conflict_stops_before_push_without_losing_either_commit(self):
        a = self.pc / "Tasks" / "tasks.md"
        b = self.phone / "Tasks" / "tasks.md"
        a.write_text("- [ ] pc edit\n", encoding="utf-8")
        b.write_text("- [ ] phone edit\n", encoding="utf-8")
        run("-C", self.phone, "add", "-A")
        run("-C", self.phone, "commit", "-m", "phone edit")
        run("-C", self.phone, "push", "origin", "main")
        with self.assertRaisesRegex(RuntimeError, "Git merge failed"):
            sync(self.pc, "main", str(self.remote))
        self.assertIn("<<<<<<<", a.read_text(encoding="utf-8"))
        self.assertNotEqual(run("-C", self.pc, "rev-parse", "HEAD"), run("-C", self.remote, "rev-parse", "HEAD"))

    def test_second_run_cannot_take_the_same_lock(self):
        lock = Path(self.temp.name) / "lock" / "run.lock"
        first = lock_file(lock)
        self.assertIsNotNone(first)
        try:
            self.assertIsNone(lock_file(lock))
        finally:
            unlock_file(first)
        again = lock_file(lock)
        self.assertIsNotNone(again)
        unlock_file(again)


if __name__ == "__main__":
    unittest.main()
