###Carlos Cantalapiedra FYM 2018
import nuke
import os

def checkMediaUI():
    # try:
    #     shot = str(os.environ['SHOT'])
    # except:
    #     shot = str(os.environ['ASSET'])
    shot = str(os.environ['PROJECT_PATH']).replace("\\", "/")
    shot = shot.replace('//dps.tv/dps', 'P:')
    unidad = os.environ['MOUNT']
    if 'V' in unidad:
        mac_path = shot.replace(unidad, '/Volumes/PROYECTOS-1').replace('\\', '/')
    else:
        mac_path = shot.replace(unidad, '/Volumes/PROYECTOS').replace('\\', '/')
    i = nuke.thisNode()
    file = i["file"].value()
    if "../" in file:
        i.knob("tile_color").setValue(4278247679)
        i.knob("note_font_color").setValue(4294967295)
    elif shot not in file and mac_path not in file:
        i.knob("tile_color").setValue(4278190335)
        i.knob("note_font_color").setValue(4294967295)
    else:
        if "/SOURCE/" in file:
            i.knob("tile_color").setValue(949013503)
        if "/VREF/" in file:
            i.knob("tile_color").setValue(4246527)
        elif "/PRECOMP/" in file:
            i.knob("tile_color").setValue(13724671)
        elif "/LAYERS/" in file:
            i.knob("tile_color").setValue(15891711)
        elif "/LGT/" in file:
            i.knob("tile_color").setValue(973127679)
        elif "/DMP/" in file:
            i.knob("tile_color").setValue(4278219519)
        elif "/REFERENCIAS/" in file:
            i.knob("tile_color").setValue(24529407)
        elif "/MEDIA/" in file:
            i.knob("tile_color").setValue(1148596479)
        elif "_CMP_v" in file:
            i.knob("tile_color").setValue(2911437567)
        elif "_ALPHA_v" in file:
            i.knob("tile_color").setValue(1790247167)
        elif "_IMP_v" in file:
            i.knob("tile_color").setValue(1563800064)
        elif "_IPL_v" in file:
            i.knob("tile_color").setValue(2483467007)

def checkMedia():
    lista = []

    preshot = nuke.root().name()
    baseshot = os.path.basename(preshot)[:-12]
    # try:
    #     shot = str(os.environ['SHOT'])
    # except:
    #     shot = str(os.environ['ASSET'])
    shot = str(os.environ['PROJECT_PATH']).replace("\\", "/")
    shot = shot.replace('//dps.tv/dps', 'P:')
    print (shot)
    unidad = os.environ['MOUNT']
    if 'V' in unidad:
        mac_path = shot.replace(unidad, '/Volumes/PROYECTOS-1').replace('\\', '/')
    else:
        mac_path = shot.replace(unidad, '/Volumes/PROYECTOS').replace('\\', '/')
    for i in nuke.allNodes("Read"):
        file = i["file"].value()
        if "../" in file:
            i.knob("tile_color").setValue(4278247679)
            i.knob("note_font_color").setValue(4294967295)
        elif shot not in file and mac_path not in file:
            i.knob("tile_color").setValue(4278190335)
            i.knob("note_font_color").setValue(4294967295)
            lista.append(i.knob("name").getValue())
        else:
            if "/SOURCE/" in file:
                i.knob("tile_color").setValue(949013503)
            if "/VREF/" in file:
                i.knob("tile_color").setValue(4246527)
            elif "/PRECOMP/" in file:
                i.knob("tile_color").setValue(13724671)
            elif "/LAYERS/" in file:
                i.knob("tile_color").setValue(15891711)
            elif "/LGT/" in file:
                i.knob("tile_color").setValue(973127679)
            elif "/DMP/" in file:
                i.knob("tile_color").setValue(4278219519)
            elif "/REFERENCIAS/" in file:
                i.knob("tile_color").setValue(24529407)
            elif "/MEDIA/" in file:
                i.knob("tile_color").setValue(1148596479)
            elif "_CMP_v" in file:
                i.knob("tile_color").setValue(2911437567)
            elif "_ALPHA_v" in file:
                i.knob("tile_color").setValue(1790247167)
            elif "_IMP_v" in file:
                i.knob("tile_color").setValue(1563800064)
            elif "_IPL_v" in file:
                i.knob("tile_color").setValue(2483467007)

    if len(lista)>0:
        text = "Material fuera de pipeline en:" + str(lista)
        nuke.message(text)
        return False
    else:
        return True

def checkMediaMessage():
    lista = []

    preshot = nuke.root().name()
    baseshot = os.path.basename(preshot)[:-12]
    # try:
    #     shot = str(os.environ['SHOT'])
    # except:
    #     shot = str(os.environ['ASSET'])
    shot = str(os.environ['PROJECT_PATH']).replace("\\", "/")
    shot = shot.replace('//dps.tv/dps', 'P:')
    unidad = os.environ['MOUNT']
    if 'V' in unidad:
        mac_path = shot.replace(unidad, '/Volumes/PROYECTOS-1').replace('\\', '/')
    else:
        mac_path = shot.replace(unidad, '/Volumes/PROYECTOS').replace('\\', '/')
    for i in nuke.allNodes("Read"):
        file = i["file"].value()
        if shot not in file and "../" not in file and mac_path not in file:
            lista.append(i.knob("name").getValue())


    if len(lista)>0:
        text = "Material fuera de pipeline en:" + str(lista)
        print(lista)
        nuke.message(text)
        return False
    else:
        return True
 
