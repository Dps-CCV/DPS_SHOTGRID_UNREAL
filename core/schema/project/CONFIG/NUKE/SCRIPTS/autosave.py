import nuke
import glob
import time
import os
import shutil

### Example that implements a rolling autosave using the autoSaveFilter callbacks
###
## autosaves roll from 0-9 eg myfile.autosave, myfile.autosave1, myfile.autosave2...
#
## To use just add 'import nukescripts.autosave' in your init.py


def onAutoSave(filename):

  ## ignore untiled autosave
  if nuke.root().name() == 'Root':
    return filename

  fileNo = 0
  files = getAutoSaveFiles(filename)

  if len(files) > 0 :
    lastFile = files[-1]
    # get the last file number

    if len(lastFile) > 0:
      try:
        fileNo = int(lastFile[-1:])
      except:
        pass

      fileNo = fileNo + 1

  if ( fileNo > 5 ):
    fileNo = 0


  if ( fileNo != 0 ):

    if (fileNo == 1):
      filenamec = filename
    else:
      filenamec = filename + str(fileNo-1)
    filename = filename + str(fileNo)

    ####Copia a local del autosave
    local = nuke.toNode("preferences").knob("localCachePath").evaluate()
    raiz = local.split('/')[0] + '\\'
    filenameCopy = os.path.join(raiz, "autosave", filenamec[3:])
    print(filename)
    directory = os.path.dirname(filenameCopy)
    if os.path.exists(local):
      if not os.path.exists(directory):
        os.makedirs(directory)
      shutil.copy(filenamec, filenameCopy)
      print("file copied to")
      print(filenameCopy)
  



  return filename



def onAutoSaveRestore(filename):

  files = getAutoSaveFiles(filename)

  if len(files) > 0:
    filename = files[-1]

  return filename

def onAutoSaveDelete(filename):

  ## only delete untiled autosave
  if nuke.root().name() == 'Root':
    return filename

  # return None here to not delete auto save file
  return None

  
def getAutoSaveFiles(filename):
  date_file_list = []
  files = glob.glob(filename + '[1-9]')
  files.extend( glob.glob(filename) )

  for file in files:
      # retrieves the stats for the current file as a tuple
      # (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime)
      # the tuple element mtime at index 8 is the last-modified-date
      stats = os.stat(file)
      # create tuple (year yyyy, month(1-12), day(1-31), hour(0-23), minute(0-59), second(0-59),
      # weekday(0-6, 0 is monday), Julian day(1-366), daylight flag(-1,0 or 1)) from seconds since epoch
      # note:  this tuple can be sorted properly by date and time
      lastmod_date = time.localtime(stats[8])
      #print image_file, lastmod_date   # test
      # create list of tuples ready for sorting by date
      date_file_tuple = lastmod_date, file
      date_file_list.append(date_file_tuple)
   
  date_file_list.sort()
  return [ filename for _, filename in date_file_list ]


nuke.addAutoSaveFilter( onAutoSave )
nuke.addAutoSaveRestoreFilter( onAutoSaveRestore )
nuke.addAutoSaveDeleteFilter( onAutoSaveDelete )



