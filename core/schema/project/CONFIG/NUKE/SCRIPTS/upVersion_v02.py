import os
import shutil
import threading
import subprocess
from subprocess import call
import nuke


def upVersionCopy(root, lastDir, lastVersion, scriptVersion, newDir):
        amount = len(os.listdir(os.path.join(root, lastDir)))
        task = nuke.ProgressTask("UpVerison")
        count = 0
        for file in os.listdir(os.path.join(root, lastDir)):
            if task.isCancelled():
                break
            task.setMessage("Step %s of %d" % (count + 1, amount))

            oldCopy = os.path.join(os.path.join(root.replace("/", "\\"), lastDir), file)
            newFile = file.replace('_v' + str('{:0>3}'.format(lastVersion)), '_v' + str(scriptVersion))
            newCopy = os.path.join(os.path.join(root.replace("/", "\\"), newDir), newFile)


            copystring = 'copy ' + oldCopy + ' ' + newCopy
            os.popen(copystring)
            count += 1
            percent = int(100 * (float(count) / (amount)))
            task.setProgress(percent)


def upVersionBase():

    if not nuke.selectedNodes() or nuke.selectedNode().Class() not in ['WriteTank', 'Write']:
        nuke.message("No Write selected")
    elif len(nuke.selectedNodes()) > 1:
        nuke.message("Select only one Write at a time")
    else:
        workDir = nuke.selectedNode().knob('tk_cached_proxy_path').value()
        folder = os.path.dirname(workDir)
        root = os.path.dirname(os.path.dirname(workDir))
        renders = []
        for a in os.listdir(root):
            if os.path.basename(folder)[:-3] in a:
                renders.append(a)
        scriptVersion = os.path.splitext(os.path.basename(nuke.root().name()))[0][-3:]
        lastDir = renders[len(renders) - 1]
        runCopy = True

        SetsPanel = nuke.Panel("Escoger version a copiar")

        listarender = ''
        for a in renders:
            listarender = listarender + ' ' + a

        SetsPanel.addEnumerationPulldown("Escoger version a copiar", listarender)
        ret = SetsPanel.show()
        if ret:
            lastDir = SetsPanel.value("Escoger version a copiar")

            lastVersion = int(lastDir[-3:])
            newDir = lastDir[:-3] + scriptVersion

            if not os.path.exists(os.path.join(root, newDir)):
                os.makedirs(os.path.join(root, newDir))

            else:
                if nuke.ask(
                        'A render folder for this version already exists. Do you want to overwrite all the files with thr previous version?'):
                    runCopy = True
                    # lastDir = renders[len(renders) - 2]
                    # lastVersion = int(lastDir[-3:])
                else:
                    runCopy = False
                    nuke.message("UpVersion was cancelled")
        else:
            runCopy = False
            nuke.message("UpVersion was cancelled")


        if runCopy == True:
            threading.Thread(None, upVersionCopy(root, lastDir, lastVersion, scriptVersion, newDir)).start()



