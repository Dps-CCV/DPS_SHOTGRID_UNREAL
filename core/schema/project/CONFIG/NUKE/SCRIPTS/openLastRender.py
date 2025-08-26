import os
import nuke
import nukescripts


def openLastRender():
    workDir = os.path.dirname(os.path.dirname(nuke.root().name()))
    renderDir = os.path.normpath(os.path.join(workDir, "IMAGES"))
    scriptVersion = os.path.splitext(os.path.basename(nuke.root().name()))[0][-3:]
    renderList = os.listdir(renderDir)
    lastDir = renderList[len(renderList) - 1]
    folder = os.path.normpath(os.path.join(renderDir, lastDir))
    files = nuke.getFileNameList(folder)

    for file in files:
        fileValue = os.path.join(folder, file)
        fileValue = nukescripts.replaceHashes(fileValue).replace('%01d', '%04d')
        # fileString = "file " + fileValue
        # readNode = nuke.createNode('Read', fileString)
        readNode = nuke.nodes.Read()
        readNode.knob('file').fromUserText(fileValue)



