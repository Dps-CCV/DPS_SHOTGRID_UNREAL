import nuke


def checkSetsWT():
    if nuke.GUI:

        if nuke.thisNode():
            try:
                n = nuke.thisNode()
                topnode = nuke.toNode("Read1")

                if topnode:
                    ###Comprobaciones de espacio de color
                    colorspace = topnode.knob('colorspace').value()
                    writecolor = n.knob('colorspace').value()

                    ###Acciones
                    oldColor = n.knob('tile_color').value()
                    if writecolor != colorspace:
                        if n.knob('tk_profile_list').value() not in ['IMAGE_PLANE','ALPHA', 'TECH_PRECOMP', 'MATTE_PAINT']:
                            n.knob('tile_color').setValue(4278190335)
                    else:
                        if n.knob('tk_profile_list').value() == 'PRECOMP':
                            n.knob('tile_color').setValue(13724671)
                        elif n.knob('tk_profile_list').value() == 'Render 16bits':
                            n.knob('tile_color').setValue(2911437567)
                        elif n.knob('tk_profile_list').value() == 'TECH_PRECOMP':
                            n.knob('tile_color').setValue(146854399)
            except:
                print("Could not catch the node to check color settings")


def RenderSetsWT():
    if nuke.GUI:

        if nuke.thisNode():
            n = nuke.thisNode()
            topnode = nuke.toNode("Read1")

            if topnode:
                ###Comprobaciones de espacio de color
                if topnode.knob('colorspace').getValue() == 0:
                    colorspace = topnode.knob('colorspace').value()[9:-1]
                else:
                    colorspace = topnode.knob('colorspace').value()
                ###Settings del nodo Write
                if n.knob('colorspace').getValue() == 0:
                    writecolor = n.knob('colorspace').value()[9:-1]
                else:
                    writecolor = n.knob('colorspace').value()

                ###Mensaje y acciones

                if writecolor != colorspace and n.knob('tk_profile_list').value() is not 'IMAGE_PLANE' and n.knob('tk_profile_list').value() is not 'ALPHA' and n.knob('tk_profile_list').value() is not 'TECH_PRECOMP' and n.knob('tk_profile_list').value() is not 'MATTE_PAINT':
                    mensajecolor = "El espacio de color del render es distinto al del Read" + "\n" + "Read: " + colorspace + " " + "\n" + "Write: " + writecolor
                    nuke.message(mensajecolor)
                    SetsPanel = nuke.Panel("Resolver discrepancias en los settings del render?")
                    SetsPanel.addBooleanCheckBox("Resolver espacio de color", True)
                    ret = SetsPanel.show()
                    if ret:
                        if SetsPanel.value("Resolver espacio de color") == 1:
                            n.knob('colorspace').setValue(colorspace)
                    else:
                        raise ValueError("Render Cancelado")
