import nuke
import os
def GenerateTools(projectMenu):
    # Build menu for custom shot templates automatically searching for nk files in template folder
    # buildTemplatesMenu.buildTemplatesMenu()

    projectMenu.removeItem('Tools')

    ToolsMenu = projectMenu.addMenu('Tools', index= 1)
    ToolsFolder = os.path.join(os.environ['PROJECT_PATH'], 'CONFIG', 'NUKE', 'TEMPLATES')




    for tool in os.listdir(ToolsFolder):
        test = os.path.join(ToolsFolder, tool).replace('\\', '/')

        if os.path.isfile(os.path.join(ToolsFolder, tool)) and os.path.splitext(ToolsFolder + '/' + tool)[1] == ".nk":

            toolName = tool.split('.')[0]
            toolCmd = 'nuke.nodePaste('+'"' + test + '"' + ")"


            ToolsMenu.addCommand(toolName, toolCmd)

    ToolsMenu.addSeparator()
    ToolsMenu.addCommand('Update Templates', lambda: GenerateTools(projectMenu))
