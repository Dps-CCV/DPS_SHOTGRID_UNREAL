import os
import shutil
import threading
import subprocess
from subprocess import call
import nuke


def upVersionCopy(renderDir, lastDir, lastVersion, scriptVersion, newDir):
    amount = len(os.listdir(os.path.join(renderDir, lastDir)))
    task = nuke.ProgressTask("UpVerison")
    count = 0
    for file in os.listdir(os.path.join(renderDir, lastDir)):
        if task.isCancelled():
            break
        task.setMessage("Step %s of %d" % (count + 1, amount))

        oldCopy = os.path.join(os.path.join(renderDir, lastDir), file)
        newFile = file.replace('_v' + str('{:0>3}'.format(lastVersion)), '_v' + str(scriptVersion))
        newCopy = os.path.join(os.path.join(renderDir, newDir), newFile)

        copystring = 'copy ' + oldCopy + ' ' + newCopy
        os.popen(copystring)
        count += 1
        percent = int(100 * (float(count) / (amount)))
        task.setProgress(percent)


def upVersionBase():
    # workDir = os.path.dirname(os.path.dirname(nuke.root().name()))
    # renderDir = os.path.normpath(os.path.join(workDir, "IMAGES"))
    # index = workDir.find("STEPS")
    # tail = workDir[index + 6:-5]
    # publishRenderDir = os.path.normpath(os.path.join(workDir[:index], "PUBLISH", "IMAGES", tail))
    # scriptVersion = os.path.splitext(os.path.basename(nuke.root().name()))[0][-3:]
    # renderList = os.listdir(publishRenderDir)
    # for i in renderList:
    #     if "NUKE" not in i:
    #         renderList.remove(i)
    # lastDir = renderList[len(renderList) - 1]
    # lastVersion = int(lastDir[-3:])
    # newDir = lastDir[:-3] + scriptVersion
    workDir = os.path.dirname(os.path.dirname(nuke.root().name()))
    renderDir = os.path.normpath(os.path.join(workDir, "IMAGES"))
    scriptVersion = os.path.splitext(os.path.basename(nuke.root().name()))[0][-3:]
    renderList = os.listdir(renderDir)
    lastDir = renderList[len(renderList) - 1]
    lastVersion = int(lastDir[-3:])
    newDir = lastDir[:-3] + scriptVersion
    runCopy = True

    if not os.path.exists(os.path.join(renderDir, newDir)):
        os.makedirs(os.path.join(renderDir, newDir))

    else:
        if nuke.ask(
                'A render folder for this version already exists. Do you want to overwrite all the files with thr previous version?'):
            runCopy = True
            lastDir = renderList[len(renderList) - 2]
            lastVersion = int(lastDir[-3:])
        else:
            runCopy = False
            nuke.message("UpVersion was cancelled")
    if runCopy == True:
        threading.Thread(None, upVersionCopy(renderDir, lastDir, lastVersion, scriptVersion, newDir)).start()



