#!/usr/bin/env python
from zipfile import ZipFile
import json,csv,datetime,os

# Change the path to your needs. Default to current.
path="."

# Using utf-8 as there were some failures on \u202f characters
notes=open('notes.csv','w', encoding="utf-8")
writer=csv.writer(notes,delimiter=',',quotechar='"')
# I removed PreviewImage and Desc from the initial
# implemenation but change for your needs.
writer.writerow(['CreationDate','BrowserURL','DescRaw'])
print('-Processing...')
for f in os.listdir(path):
  if f.endswith('.lqm'):
    arc=ZipFile(f,'r')
    memofile=arc.read('memoinfo.jlqm');
    data=json.loads(memofile)
    memo=data.get('Memo')
    memoobj=data.get('MemoObjectList')
    # Added the MemoId as a unique key
    dc=str(memo.get('Id'))+'_'+datetime.datetime.fromtimestamp(memo.get('CreatedTime')/1000).date().isoformat()
    url=memo.get('BrowserUrl')
    #img=memo.get('PreviewImage')
    #dsc=''
    dscraw=''
    isBullet=False
    # Saw there were multiple Memo objects in a Memo. Just the 
    # first object was gathered in the initial implementation.
    # Thus, I for-looped to concatenate multiple objects.
    for obj in memoobj:
      #dsc=dsc+str(memo.get('Desc'))
      if(obj.get('Type')==1):
        # Type 1 are images. 
        isBullet=False
        img=obj.get('FileName')
        if(img):
          # Used the MemoId to associate the images with the respective memo
          arc.extract('images/'+img, path+'/'+str(memo.get('Id'))+'/');
          dscraw=dscraw+'\n'+img+'\n'
      elif(obj.get('Type')==5):
        # Type 5 are bullet points.
        if(isBullet==False):
          dscraw=dscraw+'\n\u2022 '+str(obj.get('DescRaw'))+'\n'
        else:
          dscraw=dscraw+'\u2022 '+str(obj.get('DescRaw'))+'\n'
        isBullet=True
      elif(obj.get('Type')==6):
        # Type 6 are thumbnails. I didn't need these, but YMMV.
        isBullet=False
        dscraw=dscraw
      else:
        # Type 0 contains text content. 
        isBullet=False
        dscraw=dscraw+str(obj.get('DescRaw'))
    print(f,'->',dc);
    writer.writerow([dc,url,dscraw])
    arc.close()
print('\n-Output written in notes.csv file\n-Pictures are in the <Id>/images/ directory\n')
