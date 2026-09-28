#!/usr/bin/env python
"""Import notes.csv (made by lqm2csv.py) into Google Keep."""
import csv
import getpass
import os

import gkeepapi
import keyring

# Folder where notes.csv is located. Default to current.
PATH = "."
CSV_NAME = "notes.csv"
FIELDS = ["Title", "BrowserURL", "DescRaw"]
# Google blocks too frequent api calls, set the limit of notes to process at a time.
# The initial implementation had the default set to 50. I reduced to 25.
# The program will stop every X note creation and resume through user input.
RATE_LIMIT = 25
KEYRING_SERVICE = "google-keep-token"


def get_email(env, prompt):
    """Return the Gmail address from KEEP_EMAIL, else ask for it."""
    return env.get("KEEP_EMAIL") or prompt("Gmail address: ").strip()


def get_token(email, env, secret_prompt):
    """Return (master_token, came_from_keyring).

    Order: token saved in keyring by an earlier run, then KEEP_MASTER_TOKEN,
    then ask. Get a master token via
    https://github.com/simon-weber/gpsoauth#alternative-flow
    """
    saved = keyring.get_password(KEYRING_SERVICE, email)
    if saved:
        return saved, True
    token = env.get("KEEP_MASTER_TOKEN") or secret_prompt("Master token: ").strip()
    return token, False


def login(keep, email, token, token_from_keyring):
    """Log in to Keep and save the token to keyring; stop the script on failure."""
    try:
        keep.authenticate(email, token)
    except gkeepapi.exception.LoginException as error:
        advice = "Check the address and master token."
        if token_from_keyring:
            # A stale saved token would fail every run; forget it so the next
            # run falls back to KEEP_MASTER_TOKEN or asks.
            keyring.delete_password(KEYRING_SERVICE, email)
            advice = "The saved token was removed; run again with a new master token."
        raise SystemExit(f"Login failed for {email}: {error}. {advice}")
    keyring.set_password(KEYRING_SERVICE, email, keep.getMasterToken())


def read_rows(csv_path):
    """Return every row of notes.csv as a dict keyed by FIELDS."""
    # utf-8-sig also reads files re-saved by Excel, which adds a byte order mark.
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as notes:
        reader = csv.DictReader(notes)
        if reader.fieldnames != FIELDS:
            raise SystemExit(
                f"{csv_path} has columns {reader.fieldnames}, expected {FIELDS}. "
                "Re-run lqm2csv.py to rebuild it."
            )
        return list(reader)


def note_from_row(row):
    """Return (title, text): the BrowserURL, if any, on the first line, then DescRaw.

    Unfortunately gkeep api doesn't support image uploading, so image memos
    only carry a file reference.
    """
    text = row["DescRaw"]
    if row["BrowserURL"]:
        text = row["BrowserURL"] + "\n" + text
    return row["Title"], text


def import_notes(keep, rows, rate_limit=RATE_LIMIT, pause=input):
    """Create one note per row, syncing and pausing every rate_limit notes."""
    count = 0
    for count, row in enumerate(rows, start=1):
        title, text = note_from_row(row)
        print(count, title)
        keep.createNote(title, text)
        if count % rate_limit == 0:
            keep.sync()
            pause("Wait a little, then press Enter to continue")
    keep.sync()
    return count


def main():
    rows = read_rows(os.path.join(PATH, CSV_NAME))
    email = get_email(os.environ, input)
    token, token_from_keyring = get_token(email, os.environ, getpass.getpass)
    keep = gkeepapi.Keep()
    print(f"Authenticating {email}...")
    login(keep, email, token, token_from_keyring)
    print("Auth OK")
    count = import_notes(keep, rows)
    print(f"Done: {count} notes created.")


if __name__ == "__main__":
    main()
