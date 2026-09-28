"""Unit tests for lqm2csv.py and csv2keep.py.

Run from the repository root with:  python -m unittest discover tests
No Google account and no third-party packages are needed: gkeepapi and
keyring are replaced by in-memory fakes.
"""
import csv
import json
import os
import sys
import tempfile
import types
import unittest
from unittest import mock
from zipfile import ZipFile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


class FakeLoginException(Exception):
    """Stands in for gkeepapi.exception.LoginException."""


class FakeKeep:
    """Records what csv2keep does to Google Keep instead of calling Google."""

    def __init__(self, good_token="good-token"):
        self.good_token = good_token
        self.token = None
        self.notes = []
        self.sync_count = 0

    def authenticate(self, email, master_token):
        if master_token != self.good_token:
            raise FakeLoginException("BadAuthentication")
        self.token = master_token

    def getMasterToken(self):  # noqa: N802 - gkeepapi's name
        return self.token

    def createNote(self, title, text):  # noqa: N802 - gkeepapi's name
        self.notes.append((title, text))

    def sync(self):
        self.sync_count += 1


class FakeKeyring:
    """In-memory keyring with the three calls csv2keep uses."""

    def __init__(self, saved=None):
        self.saved = dict(saved or {})

    def get_password(self, service, user):
        return self.saved.get((service, user))

    def set_password(self, service, user, password):
        self.saved[(service, user)] = password

    def delete_password(self, service, user):
        del self.saved[(service, user)]


FAKE_GKEEPAPI = types.SimpleNamespace(
    Keep=FakeKeep,
    exception=types.SimpleNamespace(LoginException=FakeLoginException),
)

# csv2keep imports gkeepapi and keyring at module level; stub them when absent.
for _name, _stub in (("gkeepapi", FAKE_GKEEPAPI), ("keyring", FakeKeyring())):
    try:
        __import__(_name)
    except ImportError:
        sys.modules[_name] = _stub

import csv2keep  # noqa: E402
import lqm2csv  # noqa: E402

# Noon UTC, so the local calendar date is 2023-05-10 in any timezone within +/-11 h.
NOON_2023_05_10_MS = 1683720000000


def make_lqm(folder, name, memo, objects, images=()):
    """Build a fake QuickMemo+ export: a zip holding memoinfo.jlqm and images/."""
    path = os.path.join(folder, name)
    with ZipFile(path, "w") as archive:
        info = {"Memo": memo, "MemoObjectList": objects}
        archive.writestr("memoinfo.jlqm", json.dumps(info))
        for image in images:
            archive.writestr("images/" + image, b"fake image bytes")
    return path


def write_csv(path, header, rows, encoding="utf-8"):
    with open(path, "w", encoding=encoding, newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


class MemoTitleTests(unittest.TestCase):
    def test_title_is_memo_id_and_creation_date(self):
        memo = {"Id": 42, "CreatedTime": NOON_2023_05_10_MS}
        self.assertEqual(lqm2csv.memo_title(memo), "42_2023-05-10")


class DescribeObjectsTests(unittest.TestCase):
    def test_text_objects_are_concatenated(self):
        objects = [{"Type": 0, "DescRaw": "Hello "}, {"Type": 0, "DescRaw": "world"}]
        self.assertEqual(lqm2csv.describe_objects(objects), "Hello world")

    def test_bullet_run_starts_on_new_line_and_each_bullet_ends_one(self):
        objects = [
            {"Type": 0, "DescRaw": "List:"},
            {"Type": 5, "DescRaw": "eggs"},
            {"Type": 5, "DescRaw": "milk"},
        ]
        expected = "List:\n• eggs\n• milk\n"
        self.assertEqual(lqm2csv.describe_objects(objects), expected)

    def test_new_bullet_run_after_text_starts_on_new_line_again(self):
        objects = [
            {"Type": 5, "DescRaw": "a"},
            {"Type": 0, "DescRaw": "mid"},
            {"Type": 5, "DescRaw": "b"},
        ]
        expected = "\n• a\nmid\n• b\n"
        self.assertEqual(lqm2csv.describe_objects(objects), expected)

    def test_image_adds_its_file_name_on_its_own_line(self):
        objects = [{"Type": 0, "DescRaw": "Pic"}, {"Type": 1, "FileName": "p.jpg"}]
        self.assertEqual(lqm2csv.describe_objects(objects), "Pic\np.jpg\n")

    def test_image_without_file_name_adds_nothing(self):
        objects = [{"Type": 1}]
        self.assertEqual(lqm2csv.describe_objects(objects), "")

    def test_thumbnail_is_skipped(self):
        objects = [{"Type": 6, "DescRaw": "thumb"}, {"Type": 0, "DescRaw": "x"}]
        self.assertEqual(lqm2csv.describe_objects(objects), "x")

    def test_missing_desc_raw_adds_nothing_rather_than_none(self):
        objects = [{"Type": 0}, {"Type": 5}]
        self.assertEqual(lqm2csv.describe_objects(objects), "\n• \n")


class ConvertFolderTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.other_cwd = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.other_cwd)

    def tearDown(self):
        os.chdir(self.old_cwd)

    def csv_path(self):
        return os.path.join(self.folder, lqm2csv.CSV_NAME)

    def test_reads_lqm_files_from_folder_that_is_not_the_cwd(self):
        memo = {"Id": 1, "CreatedTime": NOON_2023_05_10_MS, "BrowserUrl": "http://a"}
        make_lqm(self.folder, "a.lqm", memo, [{"Type": 0, "DescRaw": "hi"}])
        lqm2csv.convert_folder(self.folder)
        rows = csv2keep.read_rows(self.csv_path())
        self.assertEqual(
            rows, [{"Title": "1_2023-05-10", "BrowserURL": "http://a", "DescRaw": "hi"}]
        )
        self.assertFalse(os.path.exists(os.path.join(self.other_cwd, "notes.csv")))

    def test_ignores_files_that_are_not_lqm(self):
        with open(os.path.join(self.folder, "readme.txt"), "w") as handle:
            handle.write("not a memo")
        lqm2csv.convert_folder(self.folder)
        self.assertEqual(csv2keep.read_rows(self.csv_path()), [])

    def test_extracts_images_into_memo_id_folder(self):
        memo = {"Id": 7, "CreatedTime": NOON_2023_05_10_MS}
        objects = [{"Type": 1, "FileName": "p.jpg"}]
        make_lqm(self.folder, "b.lqm", memo, objects, images=["p.jpg"])
        lqm2csv.convert_folder(self.folder)
        image = os.path.join(self.folder, "7", "images", "p.jpg")
        self.assertTrue(os.path.isfile(image))

    def test_rows_end_in_single_crlf_not_doubled_cr(self):
        memo = {"Id": 3, "CreatedTime": NOON_2023_05_10_MS}
        make_lqm(self.folder, "c.lqm", memo, [{"Type": 0, "DescRaw": "one\ntwo"}])
        lqm2csv.convert_folder(self.folder)
        with open(self.csv_path(), "rb") as handle:
            raw = handle.read()
        self.assertNotIn(b"\r\r\n", raw)
        self.assertIn(b'"one\ntwo"\r\n', raw)

    def test_multi_line_text_survives_the_round_trip(self):
        memo = {"Id": 4, "CreatedTime": NOON_2023_05_10_MS}
        objects = [{"Type": 0, "DescRaw": "café \nline two"}]
        make_lqm(self.folder, "d.lqm", memo, objects)
        lqm2csv.convert_folder(self.folder)
        rows = csv2keep.read_rows(self.csv_path())
        self.assertEqual(rows[0]["DescRaw"], "café \nline two")

    def test_returns_one_file_and_title_pair_per_memo_in_name_order(self):
        for memo_id, name in ((9, "z.lqm"), (8, "a.lqm")):
            memo = {"Id": memo_id, "CreatedTime": NOON_2023_05_10_MS}
            make_lqm(self.folder, name, memo, [])
        converted = lqm2csv.convert_folder(self.folder)
        self.assertEqual(converted, [("a.lqm", "8_2023-05-10"), ("z.lqm", "9_2023-05-10")])


class ReadRowsTests(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "notes.csv")

    def test_first_data_row_is_not_skipped(self):
        write_csv(self.path, csv2keep.FIELDS, [["1_d", "", "first"], ["2_d", "", "second"]])
        titles = [row["Title"] for row in csv2keep.read_rows(self.path)]
        self.assertEqual(titles, ["1_d", "2_d"])

    def test_byte_order_mark_from_excel_is_ignored(self):
        write_csv(self.path, csv2keep.FIELDS, [["1_d", "", "x"]], encoding="utf-8-sig")
        self.assertEqual(csv2keep.read_rows(self.path)[0]["Title"], "1_d")

    def test_csv_from_old_lqm2csv_is_refused_with_rerun_advice(self):
        write_csv(self.path, ["CreationDate", "BrowserURL", "DescRaw"], [["1_d", "", "x"]])
        with self.assertRaises(SystemExit) as caught:
            csv2keep.read_rows(self.path)
        self.assertIn("lqm2csv.py", str(caught.exception.code))


class NoteFromRowTests(unittest.TestCase):
    def test_url_goes_on_the_first_line_of_the_text(self):
        row = {"Title": "1_d", "BrowserURL": "http://a", "DescRaw": "body"}
        self.assertEqual(csv2keep.note_from_row(row), ("1_d", "http://a\nbody"))

    def test_no_url_means_text_only(self):
        row = {"Title": "1_d", "BrowserURL": "", "DescRaw": "body"}
        self.assertEqual(csv2keep.note_from_row(row), ("1_d", "body"))


class ImportNotesTests(unittest.TestCase):
    def rows(self, count):
        return [{"Title": f"{n}_d", "BrowserURL": "", "DescRaw": f"t{n}"} for n in range(count)]

    def test_every_row_becomes_a_note_in_order(self):
        keep = FakeKeep()
        with mock.patch("builtins.print"):
            count = csv2keep.import_notes(keep, self.rows(3), rate_limit=25, pause=mock.Mock())
        self.assertEqual(count, 3)
        self.assertEqual(keep.notes, [("0_d", "t0"), ("1_d", "t1"), ("2_d", "t2")])
        self.assertEqual(keep.sync_count, 1)

    def test_syncs_and_pauses_after_every_rate_limit_notes(self):
        keep = FakeKeep()
        pause = mock.Mock()
        with mock.patch("builtins.print"):
            csv2keep.import_notes(keep, self.rows(5), rate_limit=2, pause=pause)
        self.assertEqual(pause.call_count, 2)
        self.assertEqual(keep.sync_count, 3)

    def test_empty_csv_creates_nothing_but_still_syncs(self):
        keep = FakeKeep()
        count = csv2keep.import_notes(keep, [], rate_limit=2, pause=mock.Mock())
        self.assertEqual((count, keep.notes, keep.sync_count), (0, [], 1))


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.keyring = FakeKeyring()
        patcher = mock.patch.object(csv2keep, "keyring", self.keyring)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_email_comes_from_environment(self):
        prompt = mock.Mock()
        email = csv2keep.get_email({"KEEP_EMAIL": "me@gmail.com"}, prompt)
        self.assertEqual(email, "me@gmail.com")
        prompt.assert_not_called()

    def test_email_is_prompted_for_when_not_in_environment(self):
        email = csv2keep.get_email({}, mock.Mock(return_value=" me@gmail.com "))
        self.assertEqual(email, "me@gmail.com")

    def test_saved_keyring_token_is_used_first(self):
        self.keyring.set_password(csv2keep.KEYRING_SERVICE, "me@gmail.com", "saved")
        env = {"KEEP_MASTER_TOKEN": "from-env"}
        token = csv2keep.get_token("me@gmail.com", env, mock.Mock())
        self.assertEqual(token, ("saved", True))

    def test_environment_token_is_used_when_keyring_is_empty(self):
        env = {"KEEP_MASTER_TOKEN": "from-env"}
        token = csv2keep.get_token("me@gmail.com", env, mock.Mock())
        self.assertEqual(token, ("from-env", False))

    def test_token_is_prompted_for_last(self):
        secret_prompt = mock.Mock(return_value=" typed ")
        token = csv2keep.get_token("me@gmail.com", {}, secret_prompt)
        self.assertEqual(token, ("typed", False))


class LoginTests(unittest.TestCase):
    def setUp(self):
        self.keyring = FakeKeyring()
        for name, value in (("keyring", self.keyring), ("gkeepapi", FAKE_GKEEPAPI)):
            patcher = mock.patch.object(csv2keep, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def saved_token(self):
        return self.keyring.get_password(csv2keep.KEYRING_SERVICE, "me@gmail.com")

    def test_good_login_saves_token_to_keyring(self):
        csv2keep.login(FakeKeep(), "me@gmail.com", "good-token", False)
        self.assertEqual(self.saved_token(), "good-token")

    def test_rejected_login_stops_with_a_clear_message(self):
        with self.assertRaises(SystemExit) as caught:
            csv2keep.login(FakeKeep(), "me@gmail.com", "bad", False)
        self.assertIn("me@gmail.com", str(caught.exception.code))
        self.assertIn("BadAuthentication", str(caught.exception.code))

    def test_rejected_keyring_token_is_forgotten(self):
        self.keyring.set_password(csv2keep.KEYRING_SERVICE, "me@gmail.com", "stale")
        with self.assertRaises(SystemExit):
            csv2keep.login(FakeKeep(), "me@gmail.com", "stale", True)
        self.assertIsNone(self.saved_token())

    def test_rejected_environment_token_leaves_keyring_alone(self):
        self.keyring.set_password(csv2keep.KEYRING_SERVICE, "me@gmail.com", "kept")
        with self.assertRaises(SystemExit):
            csv2keep.login(FakeKeep(), "me@gmail.com", "bad", False)
        self.assertEqual(self.saved_token(), "kept")


if __name__ == "__main__":
    unittest.main()
