import nuke
import os
def loadColor():

    x = nuke.root()
    x.knob('colorManagement').setValue('OCIO')
    projectColorspace = os.environ['PROJECTCOLORSPACE']
    x.knob('floatLut').setValue(str(projectColorspace))
    x.knob('workingSpaceLUT').setValue('ACES - ACEScg')
    x.knob('int8Lut').setValue('Utility - sRGB - Texture')
    x.knob('monitorLut').setValue('ACES/Rec.709')