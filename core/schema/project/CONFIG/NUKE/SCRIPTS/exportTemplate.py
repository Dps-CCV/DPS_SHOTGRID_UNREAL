import nuke
import os
import generateTools
def exportTemplate():
  try:
    nukeExt = ".nk"
    name = nuke.getInput('Name of Tool', 'sample')
    if name:
        s = os.environ['PROJECT_PATH']+'/CONFIG/NUKE/TEMPLATES/'+ name + nukeExt

    if s is not None:
      nuke.nodeCopy(os.path.normpath(s))
      PROJECT = str(os.environ['PROJECT'])
      nukeMenu = nuke.menu('Nuke')
      projectMenu = nukeMenu.menu(PROJECT)
      generateTools.GenerateTools(projectMenu)
  except:
    pass