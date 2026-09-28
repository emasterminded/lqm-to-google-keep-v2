#!/usr/bin/env python
"""Convert LG QuickMemo+ exports (.lqm files) into a single notes.csv file."""
import csv
import datetime
import json
import os
from zipfile import ZipFile

# Folder holding the .lqm files; notes.csv and the images are written here too.
# Default to current.
PATH = "."
CSV_NAME = "notes.csv"
# I removed PreviewImage and Desc from the initial
# implementation but change for your needs.
FIELDS = ["Title", "BrowserURL", "DescRaw"]

# Memo object types found in memoinfo.jlqm.
TYPE_IMAGE = 1
TYPE_BULLET = 5
TYPE_THUMBNAIL = 6
BULLET = "• "


def memo_title(memo):
    """Return the note title: MemoId_CreationDate, the MemoId keeping it unique."""
    created = datetime.datetime.fromtimestamp(memo.get("CreatedTime") / 1000)
    return f"{memo.get('Id')}_{created.date().isoformat()}"


def describe_object(obj, after_bullet):
    """Return the text one memo object contributes to its note."""
    kind = obj.get("Type")
    if kind == TYPE_BULLET:
        start = "" if after_bullet else "\n"
        return start + BULLET + (obj.get("DescRaw") or "") + "\n"
    if kind == TYPE_IMAGE:
        # Keep can't take images, so the note gets the file name as a reference.
        image = obj.get("FileName")
        return "\n" + image + "\n" if image else ""
    if kind == TYPE_THUMBNAIL:
        # Thumbnails duplicate the images. I didn't need these, but YMMV.
        return ""
    # Type 0 (and anything unknown) is plain text.
    return obj.get("DescRaw") or ""


def describe_objects(objects):
    """Join every object of a memo, not just the first, into the note text."""
    text = ""
    after_bullet = False
    for obj in objects:
        text += describe_object(obj, after_bullet)
        after_bullet = obj.get("Type") == TYPE_BULLET
    return text


def extract_images(archive, memo_id, objects, folder):
    """Extract a memo's images to <folder>/<MemoId>/images/."""
    target = os.path.join(folder, str(memo_id))
    for obj in objects:
        image = obj.get("FileName")
        if obj.get("Type") == TYPE_IMAGE and image:
            archive.extract("images/" + image, target)


def convert_memo(lqm_path, folder):
    """Return the CSV row (Title, BrowserURL, DescRaw) for one .lqm file."""
    with ZipFile(lqm_path, "r") as archive:
        data = json.loads(archive.read("memoinfo.jlqm"))
        memo = data.get("Memo")
        objects = data.get("MemoObjectList") or []
        extract_images(archive, memo.get("Id"), objects, folder)
    return [memo_title(memo), memo.get("BrowserUrl"), describe_objects(objects)]


def convert_folder(folder):
    """Write <folder>/notes.csv from every .lqm file in folder.

    Returns a (file name, title) pair per memo, in file-name order.
    """
    converted = []
    csv_path = os.path.join(folder, CSV_NAME)
    # utf-8-sig: utf-8 (for characters like  ) with a byte order mark so
    # Excel shows accents correctly. newline="" stops Windows doubling the \r.
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as notes:
        writer = csv.writer(notes)
        writer.writerow(FIELDS)
        for name in sorted(os.listdir(folder)):
            if name.endswith(".lqm"):
                row = convert_memo(os.path.join(folder, name), folder)
                writer.writerow(row)
                converted.append((name, row[0]))
    return converted


def main():
    print("-Processing...")
    for name, title in convert_folder(PATH):
        print(name, "->", title)
    print(f"\n-Output written in {CSV_NAME} file"
          "\n-Pictures are in the <Id>/images/ directory\n")


if __name__ == "__main__":
    main()
