import shutil
import os
import threading
import nuke


def DeleteOldVersions():
    ###Resolve Images Folder
    filename = nuke.thisNode()['file'].evaluate()
    local = nuke.toNode("preferences").knob("localCachePath").evaluate()
    proj = os.environ['PROJECT']
    index = filename.lower().find(proj.lower())
    unidad = os.environ['MOUNT']
    serverFile = unidad + filename[index:]
    normalizedpath = os.path.normpath(serverFile)
    pathsep = normalizedpath.split(os.sep)
    imagesFolder = os.path.join(*pathsep[:-2])
    renderFolder = os.path.join(*pathsep[-2:-1])
    olderVersionsList = []
    for renderVersion in os.listdir(imagesFolder):
        if renderFolder[:-3] in renderVersion:
            olderVersionsList.append(renderVersion)


    def DeleteVersions():
        if len(olderVersionsList) > 4:
            oldFolder = os.path.join(imagesFolder, olderVersionsList[0])
            mens = oldFolder + " was deleted."
            shutil.rmtree(oldFolder)


    threading.Thread( None, DeleteVersions ).start()


