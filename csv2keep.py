#!/usr/bin/env python
import gkeepapi,keyring,csv

# Use your gmail address!
username='<your email address>@gmail.com'
# Change with the directory where notes.csv is located. Default to current.
path='.'
# Google blocks too frequent api calls, set the limit of notes to process at a time.
# The initial implementation had the default set to 50. I reduced to 25.
# The program will stop every X note creation and resume through user input.
ratelimit=25

# The initial implementation had a username/password authentication scheme.
# https://github.com/deviato/lqm-to-google-keep/blob/main/csv2keep.py#L21
# Unfortunately, that method is obsolete. Use master_token instead. 

# Get the master token by https://github.com/simon-weber/gpsoauth#alternative-flow
master_token = '<your Google master_token>'
keep=gkeepapi.Keep()

print('Authenticating with username and master_token...')
success=keep.authenticate(username,master_token)
token=keep.getMasterToken()
keyring.set_password('google-keep-token', username, token)
print('Auth OK')

# Using utf-8 to match how csv file was written
with open(path+'/notes.csv','r', encoding="utf-8") as notes:
  # DictReader allows reading by keys defined in lqm2csv.py
  reader=csv.DictReader(notes)
  cnt=0
  next(reader)
  for row in reader:
    # Create a note with CreationDate as title + BrowserURL + DescRaw as content. You can change the fields
    # to your needs. Unfortunately gkeep api doesn't support image uploading, so you only have a reference.
    title=row["CreationDate"]
    text=''
    #if row["PreviewImage"]: text=row["PreviewImage"]+'\n'
    if row["BrowserURL"]: text=text+row["BrowserURL"]+'\n'
    text=text+row["DescRaw"]

    cnt=cnt+1
    print(cnt,title)
    note=keep.createNote(title,text)
    if(cnt==ratelimit):
      cnt=0
      keep.sync()
      input("Wait a little, than press Enter to continue")
  keep.sync()
