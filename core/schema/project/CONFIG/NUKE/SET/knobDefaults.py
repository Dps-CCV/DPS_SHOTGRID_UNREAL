import nuke
import os

'''
NUKE ROOT DEFAULT SETTINGS
'''

nuke.knobDefault('Root.first_frame', '1001')
nuke.knobDefault('Root.last_frame', '1100')



'''
CUSTOM DEFAULT NODE SETTINGS
'''

'''
ROTO
'''
nuke.knobDefault("Roto.cliptype", "none")

'''
ROTOPAINT
'''
nuke.knobDefault("RotoPaint.cliptype", "none")

'''
FILTERERODE
'''
nuke.knobDefault("FilterErode.filter", "gaussian")

'''
SHUFFLE
'''
nuke.knobDefault("Shuffle.label", "[value in1] => [value out1]")

'''
MERGE
'''
nuke.knobDefault("Merge2.bbox", "B")

'''
CORNERPIN
'''
nuke.knobDefault("CornerPin2D.enable1", "0")
nuke.knobDefault("CornerPin2D.enable2", "0")
nuke.knobDefault("CornerPin2D.enable3", "0")
nuke.knobDefault("CornerPin2D.enable4", "0")

'''
CAMERA
''' 
# Fps and Read from file
nuke.knobDefault('Camera2.frame_rate', '24')
nuke.knobDefault('Camera2.read_from_file', '0')



'''
CARD
''' 
# Minimun amount of rows and columns
nuke.knobDefault('Card.rows', '3')
nuke.knobDefault('Card.columns', '3')


'''
COLORSPACE
'''
# Show color space transfer
nuke.knobDefault("Colorspace.label", "[value colorspace_in] to [value colorspace_out]")



'''
EXPOSURE
'''
# Change default values
nuke.knobDefault('EXPTool.colorspace', '0')
nuke.knobDefault('EXPTool.mode', '0')



'''
FRAMEHOLD
'''
# Framehold gets the current frame
nuke.addOnUserCreate(lambda: nuke.thisNode()['first_frame'].setValue(nuke.frame()), nodeClass='FrameHold')



'''
KEYMIX
'''
# channels
nuke.knobDefault('Keymix.channels', 'rgba')




'''
LOGTOLIN
'''
# Show action in label
nuke.knobDefault('Log2Lin.label', '[if {[value operation]=="lin2log"} {return "LIN > LOG"} else {return "LOG > LIN"}]')


'''
PROJECT3D
'''
# Crop disabled
nuke.knobDefault('Project3D.crop', '0')

'''
REMOVE
'''
# Show channels removed/keeped
nuke.knobDefault('Remove.label', '[string toupper [value channels]]')
nuke.knobDefault('Remove.operation', 'keep')
nuke.knobDefault('Remove.channels', 'rgba')


'''
TIMEOFFSET
'''
# Show offseted frame amount
nuke.knobDefault('TimeOffset.label', '[value time_offset] frames')


'''
TRACKER
'''
# Show reference frame and origin node when export baked
nuke.addOnCreate(lambda: nuke.thisNode()['createTransformStabilizeBaked'].setValue(nuke.thisNode()['createTransformStabilizeBaked'].value() + "\n" + "transform[\"label\"].setValue(str(nuke.thisNode().name())+\"\\n\"+\"RF\"+str(int(nuke.thisNode().knob(\"reference_frame\").value())))"), nodeClass="Tracker4")
nuke.addOnCreate(lambda: nuke.thisNode()['createPinUseReferenceFrameBaked'].setValue(nuke.thisNode()['createPinUseReferenceFrameBaked'].value() + "\n" + "pin[\"label\"].setValue(str(nuke.thisNode().name())+\"\\n\"+\"RF\"+str(int(nuke.thisNode().knob(\"reference_frame\").value())))"), nodeClass="Tracker4")
nuke.addOnCreate(lambda: nuke.thisNode()['createTransformMatchMoveBaked'].setValue(nuke.thisNode()['createTransformMatchMoveBaked'].value() + "\n" + "transform[\"label\"].setValue(str(nuke.thisNode().name())+\"\\n\"+\"RF\"+str(int(nuke.thisNode().knob(\"reference_frame\").value())))"), nodeClass="Tracker4")
nuke.addOnCreate(lambda: nuke.thisNode()['createPinUseCurrentFrameBaked'].setValue(nuke.thisNode()['createPinUseCurrentFrameBaked'].value() + "\n" + "pin[\"label\"].setValue(str(nuke.thisNode().name())+\"\\n\"+\"RF\"+str(int(nuke.frame()))"), nodeClass="Tracker4")




'''
VECTORDISTORT
'''
# Show Reference frame and also say if it is frameholding or not
nuke.knobDefault('VectorDistort.label', 'RF [value reference_frame]\n[value frame_distance]')



'''
VIEWER
'''
# Optimize viewer during playback: on
nuke.knobDefault("Viewer.freezeGuiWhenPlayBack", "1")
nuke.knobDefault("Viewer.viewerProcess", 'Rec.709 (ACES)')
# Get project name to name de viewer for use with window time tracker ActivityWatch
# def ViewerNameSet():
#     viewName = str(os.path.basename(nuke.root().knob('name').value()))[:-3] + "_Viewer"
#     nuke.knobDefault("Viewer.name", viewName)
# nuke.addOnCreate(ViewerNameSet, nodeClass="Viewer")



'''
PROJECT_DIRECTORY
'''
# Set project directory in order to use relative paths
nuke.knobDefault("Root.project.directory", "[python {nuke.script_directory()}]")

##BEFORE RENDER
nuke.knobDefault("WriteTank.BeforeRender", "RenderChecks.RenderSets()")
nuke.knobDefault("Write.BeforeRender", "RenderChecks.RenderSets()")

projectColorspace = os.environ['PROJECTCOLORSPACE']
nuke.knobDefault("WriteTank.colorspace", projectColorspace)

'''
MOTIONBLUR OFFSET
'''
nuke.knobDefault('Tracker4.shutteroffset', "centered")
nuke.knobDefault('TimeBlur.shutteroffset', "centered")
nuke.knobDefault('Transform.shutteroffset', "centered")
nuke.knobDefault('TransformMasked.shutteroffset', "centered")
nuke.knobDefault('CornerPin2D.shutteroffset', "centered")
nuke.knobDefault('MotionBlur2D.shutteroffset', "centered")
nuke.knobDefault('MotionBlur3D.shutteroffset', "centered")
nuke.knobDefault('ScanlineRender.shutteroffset', "centered")
nuke.knobDefault('Card3D.shutteroffset', "centered")