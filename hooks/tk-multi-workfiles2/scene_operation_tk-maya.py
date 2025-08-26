# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import maya.cmds as cmds

import sgtk
from sgtk.platform.qt import QtGui

HookClass = sgtk.get_hook_baseclass()


class SceneOperation(HookClass):
    """
    Hook called to perform an operation with the
    current scene
    """

    def execute(
        self,
        operation,
        file_path,
        context,
        parent_action,
        file_version,
        read_only,
        **kwargs
    ):
        """
        Main hook entry point

        :param operation:       String
                                Scene operation to perform

        :param file_path:       String
                                File path to use if the operation
                                requires it (e.g. open)

        :param context:         Context
                                The context the file operation is being
                                performed in.

        :param parent_action:   This is the action that this scene operation is
                                being executed for.  This can be one of:
                                - open_file
                                - new_file
                                - save_file_as
                                - version_up

        :param file_version:    The version/revision of the file to be opened.  If this is 'None'
                                then the latest version should be opened.

        :param read_only:       Specifies if the file should be opened read-only or not

        :returns:               Depends on operation:
                                'current_path' - Return the current scene
                                                 file path as a String
                                'reset'        - True if scene was reset to an empty
                                                 state, otherwise False
                                all others     - None
        """

        if operation == "current_path":
            # return the current scene path
            return cmds.file(query=True, sceneName=True)
        elif operation == "open":
            # do new scene as Maya doesn't like opening
            # the scene it currently has open!
            cmds.file(new=True, force=True)
            cmds.file(file_path, open=True, force=True)

            self.vaccineFix()

            # e = sgtk.platform.current_engine()
            # e.apps["tk-multi-breakdown"].show_breakdown_dialog()
            e = sgtk.platform.current_engine()
            h = e.commands['Scene Breakdown...']['callback']
            h()

            ### Routine for asking artists if the wanna change the status of the task to in progress in case it is in rev or notas status
            sg = self.parent.shotgun
            currentTask = sg.find_one('Task', [['id', 'is', context.task['id']]], ['sg_status_list'])
            if currentTask['sg_status_list'] != 'ip':
                texto ="Esta tarea está en " + currentTask['sg_status_list'] + " ¿Quieres cambiarla a In Progress?"
                SetsPanel = cmds.confirmDialog( title="Change status", message=texto, button=['Yes','No'], defaultButton='Yes', cancelButton='No', dismissString='No' )
                if SetsPanel == 'Yes':
                    data = {'sg_status_list': 'ip'}
                    sg.update('Task', context.task['id'], data)

            self.CheckFrameRate(context)

        elif operation == "save":

            self.CheckFrameRate(context)

            self.vaccineFix()

            self.unknownFix()




            # save the current scene:
            cmds.file(save=True)

        elif operation == "save_as":

            self.vaccineFix()

            self.unknownFix()

            # first rename the scene as file_path:
            cmds.file(rename=file_path)

            # Maya can choose the wrong file type so
            # we should set it here explicitely based
            # on the extension
            maya_file_type = None
            if file_path.lower().endswith(".ma"):
                maya_file_type = "mayaAscii"
            elif file_path.lower().endswith(".mb"):
                maya_file_type = "mayaBinary"

            # save the scene:
            if maya_file_type:
                cmds.file(save=True, force=True, type=maya_file_type)
            else:
                cmds.file(save=True, force=True)

        elif operation == "reset":
            """
            Reset the scene to an empty state
            """
            while cmds.file(query=True, modified=True):
                # changes have been made to the scene
                res = QtGui.QMessageBox.question(
                    None,
                    "Save your scene?",
                    "Your scene has unsaved changes. Save before proceeding?",
                    QtGui.QMessageBox.Yes
                    | QtGui.QMessageBox.No
                    | QtGui.QMessageBox.Cancel,
                )

                if res == QtGui.QMessageBox.Cancel:
                    return False
                elif res == QtGui.QMessageBox.No:
                    break
                else:
                    scene_name = cmds.file(query=True, sn=True)
                    if not scene_name:
                        cmds.SaveSceneAs()
                    else:
                        cmds.file(save=True)

            # do new file:
            cmds.file(newFile=True, force=True)
            return True
    def CheckFrameRate(self, context):
        ### Routine for checking frame rate against project settings in the web
        sg = self.parent.shotgun
        projectFps = sg.find_one('Project', [['id', 'is', context.project['id']]], ['sg_frame___rate'])
        mayaStupidUnit = cmds.currentUnit(query=True, time=True)
        timeDict = {"game": 15, "film": 24, "pal": 25, "ntsc": 30, "show": 48, "palf": 50, "ntscf": 60,
                    "23.976fps": 23.976, "29.97fps": 29.97, "29.97df": 29.97, "47.952fps": 47.952,
                    "59.94fps": 59.94, "44100fps": 44100, "48000fps": 48000}
        fps = timeDict[mayaStupidUnit]
        if float(projectFps['sg_frame___rate'].replace(",", ".")) != fps:
            texto = "El frame rate del proyecto es " + str(
                projectFps['sg_frame___rate']) + " y los settings de esta escena son " + str(
                fps) + ". Deberías comprobar los settings de la escena"
            cmds.confirmDialog(title="Change status", message=texto)

    def vaccineFix(self):
        scripts = cmds.ls(type='script')
        for i in scripts:
            if i == 'breed_gene' or i == 'vaccine_gene':
                cmds.delete(i)



    def unknownFix(self):
        ###Rutina limpieza de nodos UNKWNOWN
        nodes = cmds.ls()
        for node in nodes:
            if '_UNKNOWN' in node:
                cmds.lockNode(node, lock=False)
                cmds.delete(node)
                print(str(node) + " fue borrado")