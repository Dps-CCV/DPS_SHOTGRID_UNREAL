# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
import sys
import os
import maya.cmds as cmds

sys.path.append(os.path.dirname(__file__))
import sanityChecks_MDL
#import sanityChecks


HookBaseClass = sgtk.get_hook_baseclass()


class PrePublishHook(HookBaseClass):
    """
    This hook defines logic to be executed before showing the publish
    dialog. There may be conditions that need to be checked before allowing
    the user to proceed to publishing.
    """

    def validate(self):
        """
        Returns True if the user can proceed to publish. Override thsi hook
        method to execute any custom validation steps.
        """
        app = self.parent
        scripts = cmds.ls(type='script')
        for i in scripts:
            if i == 'breed_gene' or i == 'vaccine_gene':
                cmds.delete(i)

        scripts2 = cmds.ls(type='script')
        if app.context.step['name'] == "MODEL" or app.context.step['name'] == "MODEL_A":
            sanityChecks_MDL.createUI()
        return True