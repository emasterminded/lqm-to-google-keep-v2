# lqm-to-google-keep-v2
Huge shoutout to the original author, [deviato](https://github.com/deviato), for the initial implemenation found [here](https://github.com/deviato/lqm-to-google-keep/)!

Updated scripts to convert notes exported from LG QuickMemo+ format in csv, then import them into Google Keep

# Requirements
- A Google master_token. To obtain this, refer [here](https://github.com/simon-weber/gpsoauth#alternative-flow).
- The scripts require the installation of python with **gkeepapi** and **keyring** libs. Install with:
```
$ pip install gkeepapi keyring
```
# How To Use #
1. Export all memos from QuickMemo+ to your sdcard (Three Dots Options, Export, Select all, Export, SD Card).
2. Copy all of the exported files (.lqm) in the same directory of this scripts (or to another directory setting it accordingly in the scripts)
3. Execute the first script to convert the memos in a single csv file:
   ```
   $ python lqm2csv
   ```
   The results are a **notes.csv** file, and a directory **MemoId/images** with all of the extracted pictures.
4. Check the csv file, possibly modifying the order in which the fields will be used to fill in the memos. By default, **CreationDate** is used as the title + **BrowserURL** (if it exists) + **DescRaw** as the note text.
5. Edit **csv2keep.py** inserting your gmail address and master_token, keep the notes.csv file in the same directory, and run the script with:
   ```
   $ python csv2keep
   ```
   ~~The first time it tries to authenticate, Google could throw an error, visit the link provided by the script to bypass it.~~ This method is obsolete. Authentication is handled by a master_token in this version.
6. The program will stop every 25 memos creation (you may change this value, the initial default was 50). Check online on keep.google.com if they're ok, then press Enter to resume the script. Don't do it too quickly, or Google will block you with a Rate Limit Exceeded error.
# Limitations #
- The script will only work for text or link url notes and not for pictures, due to limitation of gkeep api. For these notes you'll only get a file reference in the memo, and all physical files in **MemoId/images** directory.
- (YMMV) If using Windows and Microsoft Excel, I'd open the csv file, save, then run the csv2keep.py script. I had a tough time figuring out why the reader did not read rows but doing this seemed to fix that (???). 
# Changelog From the Initial Implementation #
- Writing and reading csv using utf-8 (due to the \u202f character throwing errors)
- Removed PreviewImage and Desc (but you may use this for your needs)
- Added the MemoId to the Google Keep title (updated from CreationDate to MemoId_CreationDate)
- Concatenating multiple memo objects in a Memo (previously used just the first memo object)
- Type identification (Type 0 contains text content, Type 1 contains images, Type 5 contains bullet points, Type 6 contains thumbnails)
- Store images in a directory identified by the MemoId (ie, MemoId/images)
- Updated the authentication method to use a Google master_token (because the username/password, CAPTCHA method is obsolete)
- Used DictReader to read rows by keys defined in lqm2csv.py
