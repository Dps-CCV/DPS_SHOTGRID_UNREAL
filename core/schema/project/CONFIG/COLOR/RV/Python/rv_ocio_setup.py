from rv import rvtypes, commands, extra_commands
import os, re, sys
import PyOpenColorIO as OCIO

#
#   Default implementations of helper methods
#
#

DEFAULT_PIPE = {}

OCIO_ROLES = {"OCIOFile": "RVLinearizePipelineGroup", "OCIOLook": "RVLookPipelineGroup"}

OCIO_DEFAULTS = {}

METHODS = ["ocio_config_from_media", "ocio_node_from_media"]

def ReloadSource(self):
    print ("ReloadSource")
    aclip = False
    aclipIndex = 0
    clipName = ""
    try:
        tempSource = commands.sourcesAtFrame(commands.frame())[0]

        for a, val in enumerate(commands.getStringProperty(tempSource + ".tracking.info")):
            if 'catch' in val:
                catch = True
                catchIndex = a + 1

        if catch == True:
            catchValue = str(commands.getStringProperty(tempSource + ".tracking.info")[catchIndex]).replace(":", ".")
            commands.setFloatProperty("#Session.matte.aspect", [float(catchValue)], True)
            commands.setFloatProperty("#Session.matte.opacity", [float(1)], True)
            commands.setIntProperty("#Session.matte.show", [1], True)
            print("Catch ratio set to" + str(catchValue))
    except:

        print ("No catch ratio found")

    try:
        for nodesource in commands.nodesOfType("RVSource"):
            aclip = False
            aclipIndex = 0
            clipName = ""
            x = nodesource
            sourceGroup = commands.nodeGroup(x)
            lookPipeline = extra_commands.nodesInGroupOfType(sourceGroup, "RVLookPipelineGroup")[0]
            medias = commands.getStringProperty("%s.media.movie" % x)
            media = medias[0]
            if os.path.splitext(media)[1] in [".avi", ".png", ".jpg", ".jpeg", ".mov", ".mp4", ""]:
                print("8bit")
                try:
                    ocioNode = extra_commands.nodesInGroupOfType(lookPipeline, "OCIOLook")[0]
                    rv.commands.setIntProperty(ocioNode + ".ocio.active", [0])
                except:
                    pass

            else:
                ocioNode = extra_commands.nodesInGroupOfType(lookPipeline, "OCIOLook")[0]

                for a, val in enumerate(commands.getStringProperty(x + ".tracking.info")):
                    if 'shotClip' in val:
                        aclip = True
                        aclipIndex = a + 1

                if aclip == True:
                    try:
                        try:
                            clipName = str(commands.getStringProperty(x + ".tracking.info")[aclipIndex].split("|")[1][5:])
                        except:
                            clipName = ""
                        if clipName != "":
                            print("There is a clip name")
                            ocioNode = extra_commands.nodesInGroupOfType(lookPipeline, "OCIOLook")[0]
                            commands.setStringProperty(ocioNode + ".ocio_context.CLIP", [clipName])
                            commands.setIntProperty(ocioNode + ".ocio.active", [1])
                            clipresult = commands.getStringProperty(ocioNode + ".ocio_context.CLIP")[0]
                            print(clipresult)

                        else:
                            print ("No clip name found")
                            commands.setIntProperty(ocioNode + ".ocio.active", [0])

                    except:
                        print("something deeper happened")
                        pass
                elif aclip == False:
                    commands.setIntProperty(ocioNode + ".ocio.active", [0])


    except:
        print("something happened")
        pass
commands.bind('default', 'global', 'after-progressive-loading', ReloadSource, "Reload source ocio configs when fully loaded")






def ocio_config_from_media(media, attributes):

    if os.getenv("OCIO") == None:
        raise Exception("ERROR: $OCIO environment variable unset!")

    return OCIO.GetCurrentConfig()

def is_8bit(media):
    return media is not None and \
        os.path.splitext(media)[1] in [".avi", ".png", ".jpg", ".jpeg", ".mov", ".mp4", ""]



# def _get_source_shotgun_data(media):
#     """
#     Get the shotgun data from a source.
#
#     Args:
#         source (str): rv source name.
#
#     Returns:
#         dict: shotgun data as a dictionary.
#
#     """
#     try:
#         source_data = commands.getStringProperty(
#             "{}.tracking.info".format(media)
#             )
#
#         data_list = ast.literal_eval(str(source_data))
#     except:
#         return {}
#
#     return {k: v for k, v in zip(data_list, data_list[1:])}


def ocio_node_from_media(config, node, default, media=None, attributes={}):
    print ("ocio_node_from_media")

    result = [{"nodeType": d, "context": {}, "properties": {}} for d in default]
    ocioContext = {}
    nodeType = commands.nodeType(node)


    nodesource = node.split("_")[0] + "_source"



    global is_media_8bit


    if media is not None:
        is_media_8bit = is_8bit(media)




    working_space = "ACES - ACEScg"
    clip = False
    emptyClip = False
    clipIndex = 0


    if is_media_8bit:
            sourceColorSpace = "Output - Rec.709"
    else:
            sourceColorSpace =  os.environ['PROJECTCOLORSPACE']

            try:
                tracking_info_prop = "%s.tracking.info" % str(nodesource)


                for a, val in enumerate(commands.getStringProperty(tracking_info_prop)):
                    if 'shotClip' in val:
                        clip = True
                        clipIndex = a + 1
                if clip == True:
                    try:
                        clipName = str(commands.getStringProperty(tracking_info_prop)[clipIndex].split("|")[1][5:])

                    except:
                        emptyClip = True
                        clipName = ""
            except:
                clip = False
                clipName = ""

    if nodeType == "RVDisplayPipelineGroup":
        display = config.getDefaultDisplay()
        view = "Rec.709"

        displayColorSpace = config.getDisplayColorSpaceName(display, view)

        # fall back to defaults
        if displayColorSpace == "":
            display = config.getDefaultDisplay()
            view = config.getDefaultView(display)
        result = [
            {
                "nodeType": "OCIODisplay",
                "context": {},
                "properties": {
                    "ocio.function": "display",
                    "ocio.inColorSpace": working_space,
                    "ocio_display.view": view,
                    "ocio_display.display": display,
                },
            }
        ]

    elif nodeType == "RVLinearizePipelineGroup":
        result = [
                {
                    "nodeType": "OCIOFile",
                    "context": {},
                    "properties": {
                        "ocio.function": "color",
                        "ocio.inColorSpace": sourceColorSpace,
                        "ocio_color.outColorSpace": working_space,
                    },
                },
                {"nodeType": "RVLensWarp", "context": {}, "properties": {}},
            ]

    elif nodeType == "RVLookPipelineGroup":
        # If our config has a Look named "shot_specific_look" and uses the
        # environment/context variable "$SHOT" to locate any required files
        # on disk, then this is what that would likely look like:
        #
        # result = [
        #     {"nodeType"   : "OCIOLook",
        #      "context"    : {"SHOT" : os.environ.get("SHOT", "def123")}
        #      "properties" : {
        #          "ocio.function"     : "look",
        #          "ocio.inColorSpace" : OCIO.Constants.ROLE_SCENE_LINEAR,
        #          "ocio_look.look"    : "shot_specific_look"}}]

        # look = attributes.get("default_setting", "")

        if not is_media_8bit:
            if emptyClip == False:
                result = [
                    {"nodeType"   : "OCIOLook",
                     "context"    : {"CLIP": clipName},
                     "properties" : {
                         "ocio.function"     : "look",
                         "ocio.inColorSpace" : working_space,
                         "ocio_look.look"    : "Shot_GRADE"}}]
            else:
                result = []
        else:
            result = []


    return result


#
#   A couple of convenience functions
#


def isOCIOManaged(nodeType):
    def F():
        try:
            managed = commands.getIntProperty("#" + nodeType + ".ocio.active")[0] != 0
            return commands.CheckedMenuState if managed else commands.UncheckedMenuState
        except:
            return commands.UncheckedMenuState

    return F


def isOCIODisplayManaged(group):
    def F():
        try:
            groupName = "RVDisplayPipelineGroup"
            dpipeline = groupMemberOfType(group, groupName)
            dOCIO = groupMemberOfType(dpipeline, "OCIODisplay")
            managed = commands.getIntProperty(dOCIO + ".ocio.active")[0] != 0
            return commands.CheckedMenuState if managed else commands.UncheckedMenuState
        except:
            return commands.UncheckedMenuState

    return F


def ocioMenuCheck(nodeType, prop, value):
    def F():
        try:
            current = commands.getStringProperty("#" + nodeType + "." + prop)[0]
            managed = isOCIOManaged(nodeType)() == commands.CheckedMenuState
            checked = current == value and managed
            return commands.CheckedMenuState if checked else commands.NeutralMenuState
        except:
            return commands.DisabledMenuState

    return F


def ocioDisplayMenuCheck(group, display, view):
    def F():
        try:
            groupName = "RVDisplayPipelineGroup"
            dpipeline = groupMemberOfType(group, groupName)
            dOCIO = groupMemberOfType(dpipeline, "OCIODisplay")
            d = commands.getStringProperty(dOCIO + ".ocio_display.display")[0]
            v = commands.getStringProperty(dOCIO + ".ocio_display.view")[0]
            if d == display and v == view:
                return commands.CheckedMenuState
            return commands.UncheckedMenuState
        except:
            return commands.DisabledMenuState

    return F


def ocioEvent(nodeType, prop, value):
    "This function will apply its change on the current node of nodeType in the evaluation path"

    def F(event):
        commands.setStringProperty("#" + nodeType + "." + prop, [value], True)
        commands.redraw()


    return F


def ocioEventOnAllOfType(nodeType, prop, value):
    "This function will apply its change on all nodes of nodeType"
    def F(event):
        for node in commands.nodesOfType(nodeType):
            commands.setStringProperty(node + "." + prop, [value], True)
        commands.redraw()


    return F


def ocioDisplayEvent(group, display, view):
    def F(event):
        groupName = "RVDisplayPipelineGroup"
        dpipeline = groupMemberOfType(group, groupName)
        dOCIO = groupMemberOfType(dpipeline, "OCIODisplay")
        commands.setStringProperty(dOCIO + ".ocio_display.display", [display], True)
        commands.setStringProperty(dOCIO + ".ocio_display.view", [view], True)
        commands.redraw()


    return F


def groupMemberOfType(node, memberType):
    for n in commands.nodesInGroup(node):
        if commands.nodeType(n) == memberType:
            return n
    return None


def applyProps(node, contextProps, propertiesProps):
    for pprop, avalue in propertiesProps.items():
        commands.setStringProperty(node + "." + pprop, [avalue], True)
    for cprop, cvalue in contextProps.items():
        prop = node + ".ocio_context." + cprop
        if not commands.propertyExists(prop):
            commands.newProperty(prop, commands.StringType, 1)
        commands.setStringProperty(prop, [cvalue], True)


#
#   OCIOSourceSetupMode
#


class OCIOSourceSetupMode(rvtypes.MinorMode):
    """
    This mode integrates both with the base RV source_setup package and
    OCIO. The idea is that incoming source media is first examined by the
    base setup package then when appropriate, this package will switch the
    source to use OCIO. If any source uses OCIO, the display is also
    switched over to OCIO control.

    There are many assumptions here. First and foremost is that your OCIO
    worflow uses parseColorSpaceFromString() to determine incoming color
    space.

    ORDERING: this mode uses a sort key of "source_setup" with an
    ordering value of 10 which is after the default source_setup
    mode's ordering value of 0. This ensures that the default
    source_setup is run first and is then followed by the
    ocio_source_setup. If you are using this as an example for a
    different source_setup mode which you wish to have interoperate
    with the default and ocio modes use the same key of "source_setup"
    but with an ordering number that places it relative to the default
    and ocio modes. So for example if you want yours to come before
    the ocio mode, but after the default source_setup use 5 (since its
    between 0 and 10).
    """

    def useSourceOCIO(self, source, nodeType, defaultSetting=""):
        """
        This tells the source group to use OCIO instead of the RV
        linearize node. There is also ocio.look and ocio.preCache
        which can be activated in this way. For this code we're
        only assuming that OCIO is going to be used to linearize
        the source.
        """

        medias = commands.getStringProperty("%s.media.movie" % source)
        media = medias[0]

        try:
            srcAttrs = commands.sourceAttributes(source, media)
            attrDict = dict(zip([i[0] for i in srcAttrs], [j[1] for j in srcAttrs]))
            attrDict["source_node"] = source
            attrDict["default_setting"] = defaultSetting
        except:
            attrDict = {}

        if self.config == None:
            try:
                self.config = ocio_config_from_media(media, attrDict)
                OCIO.SetCurrentConfig(self.config)
                commands.defineModeMenu("OCIO Source Setup", self.buildOCIOMenu(), True)
            except Exception as inst:
                print(("ERROR: Unable to retrieve OCIO context: %s" % inst))
                return

        #
        # If we already have this OCIO node and we are reading a session,
        # then use the one we have and return
        #

        pipeSlot = OCIO_ROLES[nodeType]
        srcPipeline = groupMemberOfType(commands.nodeGroup(source), pipeSlot)
        ocioNode = groupMemberOfType(srcPipeline, nodeType)
        if ocioNode != None and self.readingSession:
            for pNode in commands.nodesInGroup(srcPipeline):
                if commands.nodeType(pNode).startswith("OCIO"):
                    commands.ocioUpdateConfig(pNode)

            print(("INFO: using %s node for %s %s" % (nodeType, source, pipeSlot)))
            return

        #
        #   Anywhere in RV there is a pipeline "slot" (File, Linearize,
        #   Look, Display, View) you can use an OCIO node.  Each OCIO node
        #   can futher be configured to act in a manner similar to the nuke
        #   OCIO color, look, or display nodes. In this case we want it to
        #   act as an OCIO color node so we can transform from the incoming
        #   file space to the ROLE_SCENE_LINEAR space (the working space)
        #
        #   You can only get the OCIO node *after* the source group has
        #   been configured to use it. Otherwise the pipelines will not
        #   have been created yet.
        #
        #   Under the hood, an RV "color" OCIO node builds a ColorSpace for
        #   inspace and outspace and uses the processor which converts from
        #   one to the other.
        #

        try:
            if pipeSlot not in DEFAULT_PIPE:
                default = commands.getStringProperty(srcPipeline + ".pipeline.nodes")
                DEFAULT_PIPE[pipeSlot] = default
            pipelineList = ocio_node_from_media(
                self.config, srcPipeline, DEFAULT_PIPE[pipeSlot], media, attrDict
            )
        except Exception as inst:
            print(
                (
                    "ERROR: Problem occurred while loading OCIO settings for %s: %s"
                    % (nodeType, inst)
                )
            )
            return

        try:
            pipeline = [p["nodeType"] for p in pipelineList]
        except KeyError as inst:
            print(
                ("ERROR: Unable to make use of ocio_node_from_media return: %s" % inst)
            )
        if pipeline == DEFAULT_PIPE[pipeSlot]:
            return

        print(("INFO: using %s node for %s %s" % (nodeType, source, pipeSlot)))

        commands.setStringProperty(srcPipeline + ".pipeline.nodes", pipeline, True)
        pipeNodes = commands.nodesInGroup(srcPipeline)
        pipeNodes.sort()
        for index, pNode in enumerate(pipelineList):
            stageOCIO = pipeNodes[index]
            try:
                applyProps(stageOCIO, pNode["context"], pNode["properties"])
            except KeyError as inst:
                print(
                    ("ERROR: Unable to apply properties to %s: %s" % (stageOCIO, inst))
                )

        commands.redraw()

    def disableSourceOCIO(self, source, nodeType):
        """
        This reverts the source group's linearize node back to using
        a native RVLinearize node.
        """

        pipeSlot = OCIO_ROLES[nodeType]
        srcPipeline = groupMemberOfType(commands.nodeGroup(source), pipeSlot)
        nodesProp = srcPipeline + ".pipeline.nodes"
        current = commands.getStringProperty(nodesProp)

        if pipeSlot not in DEFAULT_PIPE or current == DEFAULT_PIPE[pipeSlot]:
            return

        print(("INFO: resetting %s for %s" % (pipeSlot, source)))

        commands.setStringProperty(
            srcPipeline + ".pipeline.nodes", DEFAULT_PIPE[pipeSlot], True
        )
        commands.redraw()

    def useDisplayOCIO(self, group):
        """
        This installs the OCIODisplay node in the DisplayGroup's display pipeline
        in place of RV's RVDisplayColor node.

        NOTE: in RV4 all display devices are separate
        DisplayGroups. So each one can have a completely different
        view and display transform.
        """

        if self.usingOCIOForDisplay.get(group, False) or self.config == None:
            return

        groupName = "RVDisplayPipelineGroup"
        try:
            dpipeline = groupMemberOfType(group, groupName)
            if groupName not in DEFAULT_PIPE:
                default = commands.getStringProperty(dpipeline + ".pipeline.nodes")
                DEFAULT_PIPE[groupName] = default
            pipelineList = ocio_node_from_media(
                self.config, dpipeline, DEFAULT_PIPE[groupName]
            )
        except Exception as inst:
            print(
                (
                    "ERROR: Problem occurred while loading OCIO settings for OCIODisplay: %s"
                    % inst
                )
            )
            return

        try:
            pipeline = [p["nodeType"] for p in pipelineList]
        except KeyError as inst:
            print(
                ("ERROR: Unable to make use of ocio_node_from_media return: %s" % inst)
            )
        if pipeline == DEFAULT_PIPE[groupName]:
            return

        device = commands.getStringProperty(group + ".device.name")[0]
        print(("INFO: using OCIODisplay for display: %s" % device))

        dpipeline = groupMemberOfType(group, groupName)
        commands.setStringProperty(dpipeline + ".pipeline.nodes", pipeline, True)

        pipeNodes = commands.nodesInGroup(dpipeline)
        pipeNodes.sort()
        for index, pNode in enumerate(pipelineList):
            stageOCIO = pipeNodes[index]
            try:
                applyProps(stageOCIO, pNode["context"], pNode["properties"])
            except KeyError as inst:
                print(
                    ("ERROR: Unable to apply properties to %s: %s" % (stageOCIO, inst))
                )

        self.usingOCIOForDisplay[group] = True
        commands.redraw()

    def disableDisplayOCIO(self, group):
        """
        This reverts the DisplayGroup's display pipeline back to using
        RV's native RVDisplayColor node.
        """

        groupName = "RVDisplayPipelineGroup"
        dpipeline = groupMemberOfType(group, groupName)
        nodesProp = dpipeline + ".pipeline.nodes"
        current = commands.getStringProperty(nodesProp)

        if groupName not in DEFAULT_PIPE or current == DEFAULT_PIPE[groupName]:
            return

        commands.setStringProperty(
            dpipeline + ".pipeline.nodes", DEFAULT_PIPE[groupName], True
        )

        device = commands.getStringProperty(group + ".device.name")[0]
        print(("INFO: using RVDisplayColor for display: %s" % device))

        self.usingOCIOForDisplay[group] = False
        commands.redraw()

    def sourceSetup(self, event):
        """
        This function should be bound to the "source-group-complete" event. It
        will attempt to use OCIO to infer the incoming file space. If
        it succeeds, the OCIOFile node of the source group is
        activated and used to convert to the ROLE_SCENE_LINEAR space.
        """

        event.reject()  # don't eat this event -- allow others to get it too

        args = event.contents().split(";;")
        group = args[0]
        fileSource = groupMemberOfType(group, "RVFileSource")
        imageSource = groupMemberOfType(group, "RVImageSource")
        source = fileSource if imageSource == None else imageSource
        print (fileSource)
        print (imageSource)
        print (source)

        for nodeType in OCIO_ROLES.keys():
            self.useSourceOCIO(source, nodeType)

        #
        #   If this is the first OCIO color pipeline for a source assume
        #   that we also want to use OCIO for display. In this case we're
        #   just going to assume the defaults
        #

        if len(commands.nodesOfType("OCIOFile")) == 1:
            for group in commands.nodesOfType("RVDisplayGroup"):
                if not self.usingOCIOForDisplay.get(group, False):
                    self.useDisplayOCIO(group)

    def beforeSessionRead(self, event):

        event.reject()
        self.readingSession = True


    def afterSessionRead(self, event):

        event.reject()
        self.readingSession = False
        if len(commands.nodesOfType("OCIOFile")) > 1:
            for group in commands.nodesOfType("RVDisplayGroup"):
                if not self.usingOCIOForDisplay.get(group, False):
                    self.useDisplayOCIO(group)


    def ocioActiveEvent(self, nodeType):

        def F(event):
            if nodeType not in ["OCIOFile", "OCIOLook"]:
                if isOCIODisplayManaged(nodeType)() == commands.CheckedMenuState:
                    self.disableDisplayOCIO(nodeType)
                else:
                    self.useDisplayOCIO(nodeType)
                return

            evalInfo = commands.metaEvaluateClosestByType(
                commands.frame(), "RVFileSource", None
            )
            if len(evalInfo) == 0:
                evalInfo = commands.metaEvaluateClosestByType(
                    commands.frame(), "RVImageSource", None
                )
            if len(evalInfo) == 0:
                return
            source = evalInfo[0]["node"]

            if isOCIOManaged(nodeType)() == commands.CheckedMenuState:
                self.disableSourceOCIO(source, nodeType)
            else:
                self.useSourceOCIO(source, nodeType, OCIO_DEFAULTS[nodeType])


        return F

    def checkForDisplayGroup(self, event):

        event.reject()
        try:
            node = event.contents()
            if commands.nodeType(node) == "RVDisplayGroup":
                self.usingOCIOForDisplay[node] = False
                commands.defineModeMenu("OCIO Source Setup", self.buildOCIOMenu(), True)

        except Exception as inst:
            print((str(inst), node))

    def maybeUpdateViews(self, event):
        event.reject()

        if event.contents().endswith("ocio_display.display"):
            commands.defineModeMenu("OCIO Source Setup", self.buildOCIOMenu(), True)

    def selectConfig(self, event):

        try:
            config = commands.openFileDialog(
                True, False, False, "ocio|OCIO Config", None
            )[0]
            self.config = OCIO.Config.CreateFromFile(config)
            OCIO.SetCurrentConfig(self.config)
            commands.defineModeMenu("OCIO Source Setup", self.buildOCIOMenu(), True)
        except Exception as inst:
            print(inst)
    # def testOP(self, event):
    #     event.reject()  # don't eat this event -- allow others to get it too
    #     args = event.contents().split(";;")
    #     print (args)
    #
    # commands.bind('default', 'global', 'new-source', testOP, "test")

    def buildOCIOMenu(self):
        #
        #   Try to acquire OCIO config to populate the display menu
        #

        if self.config == None:
            try:
                self.config = ocio_config_from_media(None, None)
                OCIO.SetCurrentConfig(self.config)
            except Exception as inst:
                return [("OCIO", [("Choose Config...", self.selectConfig, None, None)])]

        #
        #   Make a unique entry for each device's display group
        #

        daList = []
        for display in commands.nodesOfType("RVDisplayGroup"):
            dList = [
                (
                    "Active",
                    self.ocioActiveEvent(display),
                    None,
                    isOCIODisplayManaged(display),
                ),
                ("_", None),
            ]
            for d in self.config.getDisplays():
                vList = []
                for v in self.config.getViews(d):
                    vList.append(
                        (
                            v,
                            ocioDisplayEvent(display, d, v),
                            None,
                            ocioDisplayMenuCheck(display, d, v),
                        )
                    )
                dList.append((d, vList))
            device = "  " + commands.getStringProperty(display + ".device.name")[0]
            daList.append((device, dList))

        #
        #   Apply file space changes only to the visible source
        #

        cssList = [
            ("Active", self.ocioActiveEvent("OCIOFile"), None, isOCIOManaged("OCIOFile")),
            ("_", None),
        ]
        csaList = []

        def addPath(family, tree):
            for f in family:
                for t in tree:
                    if f in t:
                        return addPath(family[1:], t)
                tree.append([f])
                return addPath(family, tree)

        families = [
            (cs.getFamily().split("/") + [cs.getName()])
            for cs in self.config.getColorSpaces()
        ]
        root = []
        for family in families:
            addPath(family, root)

        def addMenu(root, isSingle):
            if len(root) == 1:
                name = root[0]
                if isSingle:
                    OCIO_DEFAULTS.setdefault("OCIOFile", name)
                    return [
                        (
                            name,
                            ocioEvent("OCIOFile", "ocio.inColorSpace", name),
                            None,
                            ocioMenuCheck("OCIOFile", "ocio.inColorSpace", name),
                        )
                    ]
                else:
                    return [
                        (
                            name,
                            ocioEventOnAllOfType("OCIOFile", "ocio.inColorSpace", name),
                            None,
                            ocioMenuCheck("OCIOFile", "ocio.inColorSpace", name),
                        )
                    ]
            else:
                menu = []
                for r in root[1:]:
                    menu += addMenu(r, isSingle)
                return [(root[0], menu)]

        for r in root:
            cssList += addMenu(r, True)
            csaList += addMenu(r, False)

        #
        #   Apply file look changes only to the visible source
        #

        lsList = [
            ("Active", self.ocioActiveEvent("OCIOLook"), None, isOCIOManaged("OCIOLook")),
            ("_", None),
        ]
        laList = []
        for l in self.config.getLooks():
            OCIO_DEFAULTS.setdefault("OCIOLook", l.getName())
            lsList.append(
                (
                    l.getName(),
                    ocioEvent("OCIOLook", "ocio_look.look", l.getName()),
                    None,
                    ocioMenuCheck("OCIOLook", "ocio_look.look", l.getName()),
                )
            )
            laList.append(
                (
                    l.getName(),
                    ocioEventOnAllOfType("OCIOLook", "ocio_look.look", l.getName()),
                    None,
                    ocioMenuCheck("OCIOLook", "ocio_look.look", l.getName()),
                )
            )

        final = [
            ("Current Source", None, None, lambda: commands.DisabledMenuState),
            ("  File Color Space", cssList),
        ]
        if len(lsList) > 2:
            final += [("  Look", lsList)]
        final += [
            ("All Sources", None, None, lambda: commands.DisabledMenuState),
            ("  File Color Space", csaList),
        ]
        if len(laList) > 0:
            final += [("  Look", laList)]
        final += [
            ("_", None),
            ("Displays", None, None, lambda: commands.DisabledMenuState),
        ]
        final += daList

        return [("OCIO", final)]

    def __init__(self):
        rvtypes.MinorMode.__init__(self)

        self.usingOCIOForDisplay = {}
        self.readingSession = False
        self.config = None

        #
        #   Look for an implementation of the OCIOHelper on the PATH.
        #   Use the default if the import failed.
        #

        try:
            import rv_ocio_setup

            inherited = []
            for method in METHODS:
                try:
                    exec("global %s; %s = rv_ocio_setup.%s" % (method, method, method))
                    inherited.append(method)
                except AttributeError:
                    pass

            print(
                (
                    "INFO: Using %s for OCIO setup methods: %s"
                    % (rv_ocio_setup.__file__, " ".join(inherited))
                )
            )

        except ImportError:
            pass

        self.init(
            "OCIO Source Setup",
            None,
            [
                (
                    "source-group-complete",
                    self.sourceSetup,
                    "Color and Geometry Management",
                ),
                ("before-session-read", self.beforeSessionRead, ""),
                ("after-session-read", self.afterSessionRead, ""),
                ("graph-new-node", self.checkForDisplayGroup, ""),
                ("graph-node-inputs-changed", self.checkForDisplayGroup, ""),
                ("graph-state-change", self.maybeUpdateViews, ""),
            ],
            self.buildOCIOMenu(),
            "source_setup",
            10,
        )  # source_setup key used by source_setup and this mode


#
#   Dynamically looked up by the mode manager to create this mode. The name
#   matters
#


def createMode():
    return OCIOSourceSetupMode()
