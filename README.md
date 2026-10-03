# lqm-to-google-keep-v2
Huge shoutout to the original author, [deviato](https://github.com/deviato), for the initial implementation found [here](https://github.com/deviato/lqm-to-google-keep/)!

Updated scripts to convert notes exported from LG QuickMemo+ format in csv, then import them into Google Keep

# Requirements
- A Google master_token. To obtain this, refer [here](https://github.com/simon-weber/gpsoauth#alternative-flow).
- The scripts require the installation of python with **gkeepapi** and **keyring** libs. Install with:
```
$ pip install gkeepapi keyring
```
# How To Use #
1. Export all memos from QuickMemo+ to your sdcard (Three Dots Options, Export, Select all, Export, SD Card).
2. Copy all of the exported files (.lqm) into the same directory as these scripts. To use another directory, set `PATH` at the top of **both** scripts; notes.csv and the images are then written there too.
3. Execute the first script to convert the memos into a single csv file:
   ```
   $ python lqm2csv.py
   ```
   The results are a **notes.csv** file, and a directory **MemoId/images** with all of the extracted pictures.
4. Check the csv file; opening it in Excel is fine, and so is saving it from Excel. Each memo becomes one note: **Title** (MemoId_CreationDate) is the note title, and **BrowserURL** (if it exists) + **DescRaw** is the note text.
5. Run the second script, with the notes.csv file in the same directory:
   ```
   $ python csv2keep.py
   ```
   It asks for your gmail address and master_token. To skip the questions, set the environment variables `KEEP_EMAIL` and `KEEP_MASTER_TOKEN` first. After the first successful login the token is saved in your system keyring (Windows Credential Manager on Windows), so later runs only need the address. If Google rejects a saved token, the script removes it and tells you to run again with a new one.
6. The program will stop every 25 memos creation (change `RATE_LIMIT` in csv2keep.py; the initial default was 50). Check online on keep.google.com if they're ok, then press Enter to resume the script. Don't do it too quickly, or Google will block you with a Rate Limit Exceeded error.
# Limitations #
- The script will only work for text or link url notes and not for pictures, due to limitation of gkeep api. For these notes you'll only get a file reference in the memo, and all physical files in **MemoId/images** directory.
- A notes.csv made by an older version of lqm2csv.py (first column **CreationDate**) is refused; re-run lqm2csv.py to rebuild it.
# Tests #
Run from the repository root; no Google account and no extra packages needed:
```
$ python -m unittest discover tests
```
- **tests/test_units.py** - unit tests for each function of both scripts, with gkeepapi and keyring replaced by in-memory fakes.
- **tests/test_smoke.py** - one end-to-end run of lqm2csv.py then csv2keep.py per feature (convert and import, saved-token reuse and recovery, rate-limit pause), with fake gkeepapi/keyring modules that log to files instead of calling Google.
- **tests/COVERAGE.md** - which test covers which path of each function, and which smoke test covers each feature.
# Changelog From the Initial Implementation #
- Writing and reading csv using utf-8 (due to the   character throwing errors)
- Removed PreviewImage and Desc (but you may use this for your needs)
- Added the MemoId to the Google Keep title (updated from CreationDate to MemoId_CreationDate)
- Concatenating multiple memo objects in a Memo (previously used just the first memo object)
- Type identification (Type 0 contains text content, Type 1 contains images, Type 5 contains bullet points, Type 6 contains thumbnails)
- Store images in a directory identified by the MemoId (ie, MemoId/images)
- Updated the authentication method to use a Google master_token (because the username/password, CAPTCHA method is obsolete)
- Used DictReader to read rows by keys defined in lqm2csv.py
# Changelog Since v2 #
- Fixed: the first memo in notes.csv was never imported into Keep.
- Fixed: on Windows notes.csv was written with doubled line endings (`\r\r\n`), the likely reason re-saving it in Excel seemed necessary. It is now written with a byte order mark so Excel shows accents correctly, and read either way.
- Fixed: setting a directory other than the current one did not work.
- Login: credentials are no longer edited into the script (keyring, then environment variables, then prompt); a rejected login stops with a clear message instead of failing later.
- The first csv column is renamed **Title**, since it holds MemoId_CreationDate. A memo text object with no text no longer adds the word "None".
- Scripts split into functions (PEP 8) with unit and smoke tests.
