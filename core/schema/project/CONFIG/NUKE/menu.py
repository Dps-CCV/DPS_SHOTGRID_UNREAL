import nuke
import os
import formats
import presets
import knobDefaults


#DPS IMPORTS
import reviewShots
import autosave
import RenderChecks
import RenderChecks_WriteTank
import checkMedia
import exportTemplate
import generateTools
import loadFilesColor
import upVersion
import openLastRender
import RenderVersionsLimit
import copy_rendered_files
import upVersion_v02


# # Generate projectMenu to store all the templates/scripts/etc
PROJECT = str(os.environ['PROJECT'])
nukeMenu = nuke.menu('Nuke')
projectMenu = nukeMenu.addMenu(PROJECT)

generateTools.GenerateTools(projectMenu)

# Build menu for custom shot scripts
projectMenu.addSeparator()
ScriptsMenu = projectMenu.addMenu('Scripts', index= 1)
ScriptsMenu.addCommand('Review Shots', lambda: reviewShots.reviewShots())
ScriptsMenu.addCommand('Export Template', lambda: exportTemplate.exportTemplate())
ScriptsMenu.addCommand('UpVersion last Render', lambda: upVersion.upVersionBase(), 'Alt+p')
ScriptsMenu.addCommand('UpVersion last Render_v02', lambda: upVersion_v02.upVersionBase(), 'Alt+p')
ScriptsMenu.addCommand('Open last Render', lambda: openLastRender.openLastRender(), 'Ctrl+r')




nuke.addOnCreate(checkMedia.checkMediaUI, nodeClass="Read")
nuke.addOnScriptLoad(checkMedia.checkMedia)
nuke.addOnScriptSave(checkMedia.checkMediaMessage)








# nuke.addOnScriptLoad(loadFilesColor.loadColor)





#Relative path changes
#nuke.addOnScriptLoad(RelativePathChanger.AbsoluteToRelative, False)
#nuke.addOnScriptSave(RelativePathChanger.AbsoluteToRelative, False)


# ##Default ViewerProcess
# def DefaultViewerProcess():
#     nuke.knobDefault("Viewer.viewerProcess", "Rec.709 (ACES)")
# nuke.addOnScriptLoad(DefaultViewerProcess)














