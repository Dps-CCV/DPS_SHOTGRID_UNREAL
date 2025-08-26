import sgtk
import os
import nuke



def reviewShots():
    current_engine = sgtk.platform.current_engine()
    sg = current_engine.shotgun
    current_context = current_engine.context

    sequences = sg.find('Sequence', [['project.Project.name', 'is', current_context.project['name']],
                                     ['episode.Episode.code', 'not_contains', "_BID"]], ['code'])
    seqList = []
    for i in sequences:
        seqList.append(i['code'])
    seqList.insert(0, "all")

    SequencePanel = nuke.Panel("Select sequences to load")
    SequencePanel.addEnumerationPulldown('sequences to load', ' '.join(seqList))
    if SequencePanel.show() == 1:
        selectedSequence = [SequencePanel.value('sequences to load')]
        if SequencePanel.value('sequences to load') == "all":
            seqList.remove("all")
            selectedSequence = seqList

        shots = sg.find('Shot', [['project.Project.name', 'is', current_context.project['name']],
                                 ['sg_status_list', 'not_in', ['omt', 'bid', 'hld']],
                                 ['sg_sequence.Sequence.code', 'in', selectedSequence]], ['code', 'sg_status_list'])
        entries = {}
        for shot in shots:
            parafx = sg.find_one("PublishedFile",
                                 [['entity', 'is', shot],
                                  ['published_file_type.PublishedFileType.code', 'is', 'PARAFX Hiero']],
                                 ['path'], [{'field_name': 'version_number', 'direction': 'desc'}])
            vref = sg.find_one("PublishedFile",
                               [['entity', 'is', shot],
                                ['published_file_type.PublishedFileType.code', 'is', 'VREF Hiero']],
                               ['path'], [{'field_name': 'version_number', 'direction': 'desc'}])
            compRender = sg.find_one("PublishedFile", [['entity', 'is', shot],
                                                       ['published_file_type.PublishedFileType.code', 'is',
                                                        'Rendered Image']],
                                     ['path'], [{'field_name': 'version_number', 'direction': 'desc'}])
            shotdict = {}
            if parafx:
                shotdict['parafx'] = parafx['path']['local_path']
            if vref:
                shotdict['vref'] = vref['path']['local_path']
            if compRender:
                shotdict['comp'] = compRender['path']['local_path']
            shotdict['status'] = shot['sg_status_list']
            if parafx or vref or compRender:
                entries[shot['code']] = shotdict
        # for a, shot in enumerate(entries.keys()):
        paths = []
        if len(entries.keys()) == 0:
            nuke.message("No valid shots in selected sequence")
            return "No Shots in the sequence"

        def getAllPaths():
            for node in nuke.allNodes("Read"):
                paths.append(node.knob('file').getValue().replace("/", "\\"))

        getAllPaths()
        for shot in entries.keys():
            for path in paths:
                if 'vref' in entries[shot].keys():
                    if entries[shot]['vref'] and path in entries[shot]['vref']:
                        del entries[shot]['vref']
                elif 'parafx' in entries[shot].keys():
                    if entries[shot]['parafx'] and path in entries[shot]['parafx']:
                        del entries[shot]['parafx']
                elif 'comp' in entries[shot].keys():
                    if entries[shot]['comp'] and path in entries[shot]['comp']:
                        del entries[shot]['comp']


        def createReviewShots(entries):
            for a, shot in enumerate(entries.keys()):
                if not nuke.toNode(shot):
                    backdrop = nuke.createNode('BackdropNode')
                    backdrop.setYpos(200)
                    backdrop.setXpos(backdrop.xpos() + (700 * a))
                    backdrop.knob('bdwidth').setValue(500)
                    backdrop.knob('bdheight').setValue(500)
                    backdrop.knob('name').setValue(shot)
                else:
                    backdrop = nuke.toNode(shot)
                if entries[shot]['status'] == 'wtg':
                    backdrop.knob('tile_color').setValue(2290649088)
                elif entries[shot]['status'] == 'rts':
                    backdrop.knob('tile_color').setValue(3806520063)
                elif entries[shot]['status'] == 'ip':
                    backdrop.knob('tile_color').setValue(796905215)
                elif entries[shot]['status'] == 'rev':
                    backdrop.knob('tile_color').setValue(3430625023)
                elif entries[shot]['status'] == 'psu':
                    backdrop.knob('tile_color').setValue(3720675583)
                elif entries[shot]['status'] == 'nts':
                    backdrop.knob('tile_color').setValue(2284400127)
                elif entries[shot]['status'] == 'pcl':
                    backdrop.knob('tile_color').setValue(2763333375)
                elif entries[shot]['status'] == 'apr':
                    backdrop.knob('tile_color').setValue(663232511)

                for b, media in enumerate(entries[shot].keys()):
                    if media is not 'status':
                        named = shot + "///" + media
                        path = os.path.normpath(str(entries[shot][media]))
                        file = path.replace(os.sep, '/')
                        folder = os.path.dirname(file)
                        for seq in nuke.getFileNameList(folder):
                            read = nuke.nodes.Read(name=named)
                            fixfile = folder + '/' + seq
                            fileValue = nukescripts.replaceHashes(fixfile).replace('%01d', '%04d')
                            read.knob('file').fromUserText(fileValue)
                            read.setYpos(250)
                            read.setXpos(backdrop.xpos() + 50 + (150 * b))

        createReviewShots(entries)


