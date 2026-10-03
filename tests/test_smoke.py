"""Smoke tests: run lqm2csv.py then csv2keep.py end to end, as a user would.

Both scripts run as real subprocesses. csv2keep.py is pointed at fake gkeepapi
and keyring modules (written to a temp folder and put first on PYTHONPATH) that
log to files instead of calling Google or the Windows credential store.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from test_units import NOON_2023_05_10_MS, csv2keep, make_lqm

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAKE_GKEEPAPI = '''
import json, os
from types import SimpleNamespace

class LoginException(Exception):
    pass

exception = SimpleNamespace(LoginException=LoginException)

def _log(entry):
    with open(os.environ["FAKE_KEEP_LOG"], "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\\n")

class Keep:
    def authenticate(self, email, master_token):
        if master_token != "good-token":
            raise LoginException("BadAuthentication")
        self._token = master_token

    def getMasterToken(self):
        return self._token

    def createNote(self, title, text):
        _log({"note": [title, text]})

    def sync(self):
        _log({"sync": True})
'''

FAKE_KEYRING = '''
import json, os

def _load():
    path = os.environ["FAKE_KEYRING_FILE"]
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)

def _save(store):
    with open(os.environ["FAKE_KEYRING_FILE"], "w", encoding="utf-8") as handle:
        json.dump(store, handle)

def get_password(service, user):
    return _load().get(service + "|" + user)

def set_password(service, user, password):
    store = _load()
    store[service + "|" + user] = password
    _save(store)

def delete_password(service, user):
    store = _load()
    del store[service + "|" + user]
    _save(store)
'''


class EndToEndTests(unittest.TestCase):
    """One workflow per feature: convert + import, saved-token recovery, rate-limit pause."""

    def setUp(self):
        self.work = tempfile.mkdtemp()
        fakes = tempfile.mkdtemp()
        for name, source in (("gkeepapi.py", FAKE_GKEEPAPI), ("keyring.py", FAKE_KEYRING)):
            with open(os.path.join(fakes, name), "w", encoding="utf-8") as handle:
                handle.write(source)
        self.keep_log = os.path.join(fakes, "keep.log")
        self.keyring_file = os.path.join(fakes, "keyring.json")
        self.env = dict(
            os.environ,
            PYTHONPATH=fakes,
            PYTHONIOENCODING="utf-8",
            FAKE_KEEP_LOG=self.keep_log,
            FAKE_KEYRING_FILE=self.keyring_file,
            KEEP_EMAIL="me@gmail.com",
        )

    def make_exports(self, memos):
        """memos: (MemoId, objects, image file names) per .lqm file."""
        for memo_id, objects, images in memos:
            memo = {"Id": memo_id, "CreatedTime": NOON_2023_05_10_MS}
            make_lqm(self.work, f"memo{memo_id:02}.lqm", memo, objects, images)

    def run_script(self, name, token=""):
        env = dict(self.env, KEEP_MASTER_TOKEN=token)
        return subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, name)],
            cwd=self.work, env=env, input="\n" * 10,
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )

    def keep_entries(self):
        if not os.path.exists(self.keep_log):
            return []
        with open(self.keep_log, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle]

    def notes(self):
        return [entry["note"] for entry in self.keep_entries() if "note" in entry]

    def saved_tokens(self):
        if not os.path.exists(self.keyring_file):
            return {}
        with open(self.keyring_file, encoding="utf-8") as handle:
            return json.load(handle)

    def test_memos_are_converted_and_imported_and_rerun_reuses_saved_token(self):
        self.make_exports((
            (1, [{"Type": 0, "DescRaw": "first memo"}], ()),
            (2, [{"Type": 0, "DescRaw": "List"}, {"Type": 5, "DescRaw": "eggs"}], ()),
            (3, [{"Type": 1, "FileName": "p.jpg"}], ("p.jpg",)),
        ))
        converted = self.run_script("lqm2csv.py")
        self.assertEqual(converted.returncode, 0, converted.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.work, "3", "images", "p.jpg")))

        imported = self.run_script("csv2keep.py", "good-token")
        self.assertEqual(imported.returncode, 0, imported.stderr)
        expected = [
            ["1_2023-05-10", "first memo"],
            ["2_2023-05-10", "List\n• eggs\n"],
            ["3_2023-05-10", "\np.jpg\n"],
        ]
        self.assertEqual(self.notes(), expected)
        self.assertEqual(self.keep_entries()[-1], {"sync": True})
        self.assertEqual(self.saved_tokens(), {"google-keep-token|me@gmail.com": "good-token"})

        # Later runs need only the address: no KEEP_MASTER_TOKEN, nothing typed.
        rerun = self.run_script("csv2keep.py")
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertEqual(self.notes(), expected * 2)

    def test_rejected_saved_token_is_removed_and_no_note_is_created(self):
        self.make_exports(((1, [{"Type": 0, "DescRaw": "memo"}], ()),))
        with open(self.keyring_file, "w", encoding="utf-8") as handle:
            json.dump({"google-keep-token|me@gmail.com": "stale-token"}, handle)
        self.run_script("lqm2csv.py")
        imported = self.run_script("csv2keep.py", "good-token")
        self.assertEqual(imported.returncode, 1)
        self.assertIn("Login failed for me@gmail.com", imported.stderr)
        self.assertEqual(self.keep_entries(), [])
        self.assertEqual(self.saved_tokens(), {})

    def test_import_syncs_and_pauses_after_every_rate_limit_notes(self):
        count = csv2keep.RATE_LIMIT + 1
        self.make_exports(
            (n, [{"Type": 0, "DescRaw": f"memo {n}"}], ()) for n in range(1, count + 1)
        )
        self.run_script("lqm2csv.py")
        imported = self.run_script("csv2keep.py", "good-token")
        self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertEqual(imported.stdout.count("press Enter to continue"), 1)
        entries = self.keep_entries()
        self.assertEqual(entries[csv2keep.RATE_LIMIT], {"sync": True})
        self.assertEqual(len(self.notes()), count)
        self.assertEqual(entries[-1], {"sync": True})

if __name__ == "__main__":
    unittest.main()
