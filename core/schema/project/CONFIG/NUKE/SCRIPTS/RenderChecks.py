import nuke


def checkSets():
    if nuke.GUI:

        n = nuke.thisNode()
        group = ''.join(nuke.thisNode().fullName().split('.')[:-1])
        groupNode = nuke.toNode(group)

        topnode = nuke.toNode("Read1")
        if topnode:
            ###Comprobaciones de espacio de color
            if topnode.knob('colorspace').getValue() == 0:
                colorspace = topnode.knob('colorspace').value()[9:-1]
            else:
                colorspace = topnode.knob('colorspace').value()

            ##Settings del nodo Write
            if n.knob('colorspace').getValue() == 0:
                writecolor = n.knob('colorspace').value()[9:-1]
            else:
                writecolor = n.knob('colorspace').value()

            ###Acciones
            oldColor = n.knob('tile_color').value()
            if writecolor != colorspace:
                if groupNode.knob('tk_profile_list').value() not in ['IMAGE_PLANE', 'ALPHA', 'TECH_PRECOMP', 'MATTE_PAINT']:
                    groupNode.knob('tile_color').setValue(4278190335)
            else:
                if groupNode.knob('tk_profile_list').value() == 'PRECOMP':
                    groupNode.knob('tile_color').setValue(13724671)
                elif groupNode.knob('tk_profile_list').value() == 'TECH_PRECOMP':
                    groupNode.knob('tile_color').setValue(146854399)
                elif groupNode.knob('tk_profile_list').value() == 'ALPHA':
                    groupNode.knob('tile_color').setValue(1790247167)
                elif groupNode.knob('tk_profile_list').value() == 'IMAGE_PLANE':
                    groupNode.knob('tile_color').setValue(1563800064)
                elif groupNode.knob('tk_profile_list').value() == 'Render 16bits':
                    groupNode.knob('tile_color').setValue(2911437567)
                elif groupNode.knob('tk_profile_list').value() == 'MATTE_PAINT':
                    groupNode.knob('tile_color').setValue(645572863)
                else:
                    groupNode.knob('tile_color').setValue(2911437567)


def RenderSets():
    if nuke.GUI:
        n = nuke.thisNode()
        group = ''.join(nuke.thisNode().fullName().split('.')[:-1])
        groupNode = nuke.toNode(group)

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

            if writecolor != colorspace:
                if 'IMAGE_PLANE' not in groupNode.knob('tk_profile_list').value() and 'ALPHA' not in groupNode.knob('tk_profile_list').value() and 'TECH_PRECOMP' not in groupNode.knob('tk_profile_list').value() and 'MATTE_PAINT' not in groupNode.knob('tk_profile_list').value():
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



