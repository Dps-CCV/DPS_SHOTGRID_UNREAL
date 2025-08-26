import nuke
import os

# Add Nuke pipeline paths
additionalPaths = [
    './SCRIPTS',
    './TEMPLATES',
    './SET',
    './ICONS'
]


for p in additionalPaths:
    nuke.pluginAddPath(p)

nuke.pluginAddPath('./SCRIPTS/rvnuke')

import copy_rendered_files
import RenderVersionsLimit
import RenderChecks_WriteTank


nuke.knobDefault('Root.colorManagement', 'OCIO')
nuke.knobDefault("Viewer.viewerProcess", 'Rec.709 (ACES)')
projectColorspace = os.environ['PROJECTCOLORSPACE']
nuke.knobDefault('Root.floatLut', projectColorspace)
nuke.knobDefault('Root.workingSpaceLUT', 'ACES - ACEScg')
nuke.knobDefault('Root.int8Lut', 'Utility - sRGB - Texture')
nuke.knobDefault('Root.monitorLut', 'ACES/Rec.709 (ACES)')
nuke.knobDefault('Root.monitorOutLUT', 'Rec.709')
nuke.knobDefault("Viewer.freezeGuiWhenPlayBack", "1")
nuke.knobDefault("Viewer.viewerProcess", "Rec.709 (ACES)")









