import nuke, os, shutil, threading, platform, subprocess

class cacheAndCopy:
	def cacheFiles(self):
		self.file = os.path.basename(nuke.thisNode()['file'].value())
		self.cache = "D:/RenderCache"
		self.target = os.path.dirname(nuke.thisNode()['file'].value())
		self.targetStr = os.path.dirname(nuke.thisNode()['file'].evaluate())
		self.originalPath = nuke.thisNode()['file'].getText()
		self.fileStr = nuke.thisNode()['file'].evaluate()
		self.RenderPath = self.cache+"/" + self.fileStr[3:-8]
		self.filextension = self.fileStr[-4:]

		nuke.thisNode()['file'].setValue(self.RenderPath + "%04d" + self.filextension)

		if not os.path.exists(self.cache):
		    os.mkdir(self.cache)
		if not os.path.exists(os.path.abspath(self.targetStr)):
		    os.mkdir(os.path.abspath(self.targetStr))


	def createFolders(self):
		self.filename = nuke.thisNode()['file'].evaluate()
		print("createfolders_filename" + os.path.normpath(self.filename))
		# local = nuke.toNode("preferences").knob("localCachePath").evaluate()
		# print("toke local:")
		# print (local)
		proj = os.environ['PROJECT']
		index = self.filename.lower().find(proj.lower())
		unidad = os.environ['MOUNT'] + "\\"
		serverFile = os.path.dirname(unidad + self.filename[index:])
		print("createfolders_serverfile" + os.path.normpath(serverFile))
		if not os.path.exists(os.path.abspath(os.path.normpath(serverFile))):
		    os.makedirs(os.path.abspath(os.path.normpath(serverFile)))
		if not os.path.exists(os.path.abspath(os.path.dirname(self.filename))):
		    os.makedirs(os.path.abspath(os.path.dirname(self.filename)))

	def copyFiles(self):
		self.filename = nuke.thisNode()['file'].evaluate()
		print("copyFiles_filename" + os.path.normpath(self.filename))

		if platform.system() == 'Windows':
			copyCommand = 'copy '
		else:
			copyCommand = 'cp '
		# local = nuke.toNode("preferences").knob("localCachePath").evaluate()
		# print("toke local:")
		# print (local)
		proj = os.environ['PROJECT']
		index = self.filename.lower().find(proj.lower())
		unidad = os.environ['MOUNT'] + "\\"
		serverFile = unidad + self.filename[index:]
		print("copyFiles_serverfile" + os.path.normpath(serverFile))
		serverFileNorm = os.path.normpath(serverFile)
		filenameNorm = os.path.normpath(self.filename)
		copystring = copyCommand + filenameNorm + ' ' + serverFileNorm
		print (copystring)

		subprocess.call(copystring, shell=True)
		os.remove(self.filename)



	def resetNode(self): 
		nuke.thisNode()['file'].setValue(self.originalPath)

