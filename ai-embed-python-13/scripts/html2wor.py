# HTML to Word
#
# A tool for crawling from a HTML base, and creating a windows .HLP file
# via Word6.

import sys
import htmllib
import ole
import string
import win32ui
import win32api
import Para
import rand
import urllib
import urlparse
import os
import regsub
import time
import formatter
import glob
# html2word
# Ive tried to put most configurable options here.
#
# Directory where all files will be written
projectDirectory="d:\\temp\\wordtemp"

trace = 0               # trace level - 0-?
addDocsToWordMRU = 0    # add saved docs in words mru list?
doBuild = 1             # Should I build the .hlp file after building the rtf/hpj?
doRun = 1               # Should I run the help file afterwards?
minimizeWord = 1        # Should I minimize Word as I am building
restartWordDocCount = 50# After how many documents should I shut down word?
contentsTitle="Contents"# The HTML title to use as the help files contents page.
templateName = "html2wor.dot"
#templateName = "Normal.dot"
closeWordDocuments = 1
validHosts = [''] # by default, only process local hrefs.

# MakeKeyword is used to turn a "virtual" keywork into a keyword.  Note that if a
# <META tag specifies a keyword, it is not passed through this, it is used
# literally
# This implementation handles "topic--subtopic" into "subtopic"
#                             "1.2.3  Topic" into "Topic"
#                             "The topic" into "topic"
# etc.
keyword_subtopic_seps = ['--','==']
keyword_ignore_prefixes = ['the','a','built-in','module','python','standard']
keyword_ignore_chars = string.digits+'.,-=+;~*'

def MakeKeyword( keyword ):
	if keyword is None: return None
	for sep in keyword_subtopic_seps:
		s=string.splitfields(keyword, sep)
		if len(s)>1:
			keyword = string.strip(s[-1])
			break
	words = string.split(keyword)
	start = 0
	for word in words:
		use = 1
		if string.lower(word) in keyword_ignore_prefixes:
			use = 0
		if use:
			use = 0
			for char in word:
				if string.find(keyword_ignore_chars, char)<0:
					use = 1
					break
		if not use:
			start = start + 1
			continue
		break
	return string.strip(string.join(words[start:]))

error = "html2word error"

def Trace(text, traceLevel=0):
	if trace>=traceLevel:
		print text
	# always flush, so any print statements are shown
	sys.stdout.flush()

#def MakeCleanContextString(str):
#	return regsub.gsub("[^A-Za-z0-9\\._]", "_", str)

################################################################
#
# Word Session class
#
################################################################
class WordSession:
	"Manages an OLE session with Microsoft Word"
	def __init__(self):
		self.wb = None
		self.noOfGets = 0
	def __del__(self):
		self.close()
	def close(self):
		if self.wb:
			try:
				self.wb._release_()	# release the WordBasic handle.
			except:
				Trace("** Could not be release handle to WordBasic **")
			self.wb = None
	def GetWordBasicObject(self):
		if self.wb is None or self.noOfGets == restartWordDocCount:
			self._SetupWordBasic()
			self.noOfGets = 0
		self.noOfGets = self.noOfGets + 1
		return self.wb
		

	def _InsertButtonInfo( self, buttons ):
		butStr = ''
		for id, text, context in buttons.values():
			if len(butStr)>0:
				butStr = butStr + ';'
			if context:
				butStr = butStr + 'EB("%s");CBB("%s", "JumpId(`\', `%s\')")' % (id, id,context)
			else:
				butStr = butStr + 'DB("%s")' % id
		if len(butStr)==0:
			return

		self.wb.StartOfDocument._proc_()
		self.InsertFootnoteText( "!", butStr )

	def _SetupWordBasic(self):
		if self.wb:
			win32ui.SetStatusText("Shutting down Word...", 1)
			self.wb._release_()
			self.wb = None
		win32ui.PumpWaitingMessages()
		win32ui.SetStatusText("Starting Microsoft Word...", 1)
		self.wb = ole.WordBasic()
		win32ui.PumpWaitingMessages()
		if minimizeWord and self.wb.AppMinimize()==0:
			win32ui.SetStatusText("Minimising Word...", 1)
			self.wb.AppMinimize._proc_()
		win32ui.PumpWaitingMessages()

	def FinishWordDocument( self, fileName, title, buttons ):
		Trace("Saving Word document '%s'" % fileName, 2)
		# Clean up and save the finished file.
		if title:
			self.wb.StartOfDocument._proc_()
			self.wb.InsertPara()
			self.wb.CharLeft()
			self.InsertFootnoteText( "$", title )
			self.wb.Style("Title")
			self.wb.Insert(title)
		self._InsertButtonInfo(buttons)

		self.wb.FileSaveAs( fileName, 6, 0, '', addDocsToWordMRU )
		if closeWordDocuments:
			self.wb.FileClose()

	def CreateWordDocument( self, context ):
		self.wb.FileNew( templateName )
		self.wb.FileTemplates._proc_(0, templateName, 1) # link to the style sheet.
		self.wb.ViewNormal._proc_()
		self.InsertFootnoteText( "#", context )

	def InsertFootnoteText( self, ref, text ):
		self.wb.InsertFootnote._proc_( ref )
		self.wb.Insert._proc_(text)
		self.wb.OtherPane._proc_()
#		self.wb.CharLeft._proc_()
#		if self.wb.Selection()==" ":
#			self.wb.EditClear._proc_(1)
#		self.wb.CharLeft._proc_(1)
#		self.wb.CharRight._proc_(1,1)
#		self.wb.Style._proc_("Footnote Reference")
#		self.wb.CharRight._proc_(1,0)
#		self.wb.ResetChar._proc_()
#		self.wb.ResetPara._proc_()

################################################################
#
# HRef and HRefManager classes
#
################################################################
class HRef:
	"HRef class.  Do not construct directly"
	def __init__(self, href, status, context):
		self.status = status
		self.context = context
		self.msg = None
		self.href = href
	def __repr__(self):
		return "HRef object: href=%s, status=%d, msg=%s, context=%s" %(self.href, self.status, `self.msg`, self.context)
	def SetStatus(self, status, msg = None):
		self.status = status
		self.msg = msg
	def GetStatus(self):
		return self.status
	def GetContext(self):
		if self.context is None:
			raise error, "Invalid context"
		return self.context

class HRefManager:
	# Some constants for html processing status.
	STATUS_NONE = 0
	STATUS_PROCESSED = 1
	STATUS_ERROR = 2
	def __init__(self, statusCallback):
		self.contextCounter = 0
		self.refsProcessed = 0
		# hrefs is a dictionary of hrefs.
		# each item HRef object
		self.hrefs = {}
		self.statusCallback = statusCallback
	def close(self):
		if self.hrefs:
			self.hrefs = None
	def Dump(self):
		print "HRef Manager has %d items:" % len(self.hrefs)
		for key, value in self.hrefs.items():
			print " %s: %s" % (key, value)
	def GetBaseHRefList(self, status):
		ret = []
		for key, item in self.hrefs.items():
			if item.status==status:
				if string.find(key, "#") < 0:
					ret.append(item)
		return ret
			
	def GetNumHRefs(self):
		return len(self.hrefs)
	def GetNumHRefsProcessed(self):
		return self.refsProcessed
	def GetFirstUnprocessedRef(self):
		for key, href in self.hrefs.items():
			if href.status == HRefManager.STATUS_NONE:
				pos = string.find(key, "#")
				if pos < 0:
					# Top level
					return key
				else:
					# sub-reference.  Check the full reference
					parentRef = key[:pos]
					try:
						parent = self.hrefs[parentRef]
						if parent.status==HRefManager.STATUS_NONE:
							return parentRef # Use my parent.
						else:
							# parent had an error.  Set the same error for me.
#							Trace("*** WARNING - Parent and child href status not consistent.  Parents status used. ***")
							href.status = parent.status
							href.msg = parent.msg
							self.refsProcessed = self.refsProcessed + 1
							# and continue around the loop
					except KeyError: # never seen parent - must be unprocessed
#						print "%s parent %s has never been seen!" % (key,parentRef)
						return parentRef
					
		return None
	def _SetHRefStatus(self, ob, newStatus):
		if not newStatus is None:
			oldStatus = ob.status
			ob.status = newStatus
			if oldStatus==HRefManager.STATUS_NONE and newStatus <> HRefManager.STATUS_NONE: self.refsProcessed = self.refsProcessed + 1				
			self.statusCallback()

	def AddHRef( self, href, newStatus=None ):
		"Add a string href to the set of hrefs"
		if len(href)==0 or href[0] == "#":
			raise error, "Bad HRef - %s" % href
		try:
			ob = self.hrefs[href]
			self._SetHRefStatus(ob, newStatus)
		except KeyError:
			context = "C_%05d" % self.contextCounter
			self.contextCounter = self.contextCounter + 1
			if newStatus is None: newStatus = HRefManager.STATUS_NONE
			if newStatus <> HRefManager.STATUS_NONE: self.refsProcessed = self.refsProcessed + 1
			ob = HRef(href, newStatus, context)
			self.statusCallback()
			self.hrefs[href] = ob
		return ob
	def GetHRefObject(self, hrefStr):
		try:
			return self.hrefs[hrefStr]
		except KeyError:
			print "Dumping HRef List..."
			self.Dump()
			raise error, "Requested href '%s' is not in list!" % hrefStr

	def SetHRefStatus( self, hrefStr, newStatus ):
		"Set a html reference's status.  Reference must already be in the list."
		try:
			ob = self.hrefs[hrefStr]
			self._SetHRefStatus( ob, newStatus )
		except KeyError:
			raise error, "Requested href '%s' is not in list!" % hrefStr
	def GetHRefsContextString(self, href ):
		try:
			return self.hrefs[href].GetContext()
		except KeyError:
			raise ValueError, "The href %s does not have a context string" % href

################################################################
#
# Contents Buidler and Heading Item
#
################################################################
class HeadingItem:
	"""A heading item that recognises "1.2.3" style numbering, and can
	sort itself accordingly"""
	def __init__(self, text, href):
		pos = string.find(text, " ")
		try:
			outline = text[:pos]
			for char in outline:
				if char not in '0123456789.':
					raise ValueError
			text = string.strip(text[pos+1:])
		except ValueError, IndexError:
			outline = ''
		self.text = text
		self.outline = outline
		self.href = href
	def __repr__(self):
		return "HeadingItem: %s-%s <%s>" % (self.outline,self.text, self.href)
	def __cmp__(self, other):
		selfList = string.splitfields(self.outline,'.')
		otherList = string.splitfields(other.outline,'.')
		top = min(len(selfList),len(otherList))
		for i in range(top):
			res = cmp(string.atoi(selfList[i]), string.atoi(otherList[i]))
			if res:
				return res
		return cmp(len(selfList), len(otherList))
	def GetLevel(self):
		return len(string.splitfields(self.outline,'.'))-1

class ContentsBuilder:
	def __init__(self):
		self.contentsRoot = ("Root", 0, [])
		self.savedContentsRoot = None
		self.headingList = []
	def AddHeading(self, data, hrefOb):
#		print "adding ", data, hrefOb
		self.headingList.append(HeadingItem(data, hrefOb))
	def _CountContents(self, object):
		ret = 0
		for subobject in object[2]:
			ret = ret + self._CountContents(subobject) + 1
		return ret
	def CheckBestContents(self):
		"Called when the current contents set is complete."
		# Ahhh - for now, take the first.
		if self.savedContentsRoot is None:
			self.savedContentsRoot = self.contentsRoot
			self.contentsRoot = None
#			print "Saved contents root:"
#			self.PrintContentsTree()
		return
	def PrintContentsTree(self):
		print "Dumping contents tree"
		ob = self.savedContentsRoot
		if ob is None:
			print "<<None!!>>"
		else:
			self._PrintContentsHelper(ob, 0)
	def _PrintContentsHelper(self, object, level):
		print " " * (level*2),
		print object[0], object[1]
		sys.stdout.flush()
		for subobject in object[2]:
			self._PrintContentsHelper(subobject, level+1)
	def RemoveUnusedHeadingItems(self):
		newList = []
		for item in self.headingList:
			if len(item.outline)<>0:
				newList.append(item)
#			else:
#				print "Removing unused item ", item
		self.headingList = newList
	def HaveContentsData(self):
		# If we have _any_ contents entries, we are ok.
		if len(self.savedContentsRoot[2])<>0:
			return 1
		# check usable heading items
		self.RemoveUnusedHeadingItems()
		rc = len(self.headingList)<>0
		if not rc:
			Trace("No contents data available for help file",0)
		return rc
	
	def _CountContentsTree(self, item):
		num = 0
		for sub in item[2]:
			num = num + 1 + self._CountContentsTree(sub)
		return num
	def WriteContentsData(self, title, fp):
		if not self.HaveContentsData():
			raise error, "No contents data available."
		if title is None: title = "Help File"
		fp.write ("1 %s\n" % title)
		# Now decide the most appropriate contents tree to use.
#		numTree = self._CountContentsTree(self.savedContentsRoot)
		self.RemoveUnusedHeadingItems()
		if len(self.headingList) == 0:
			self.PrintContentsTree()
			for item in self.savedContentsRoot[2]:
				self._WriteContentsHelper(item, 2, fp)
		else:
			self.headingList.sort()
#			print "Heading Items"
#			for item in self.headingList:
#				print item.outline, item.GetLevel(), item.text, "->", item.href

			lastItem = self.headingList[0]
			for item in self.headingList[1:]:
				thisLevel = item.GetLevel()
				lastLevel = lastItem.GetLevel()
				if thisLevel > lastLevel:
					# treat as folder
					fp.write( "%d %s\n" % (lastLevel+1, lastItem.text))
				else:
					fp.write( "%d %s=%s\n" % (lastLevel+1, lastItem.text,lastItem.href.context))
				lastItem = item
			# now write the last one.  Must be a loc.
			fp.write( "%d %s=%s\n" % (lastItem.GetLevel()+1, lastItem.text,lastItem.href.context))
			
	def _WriteContentsHelper(self, item, level, fp):
		if len(item[2])==0:
			fp.write( "%d %s=%s\n" % (level, item[0], item[1].context))
		else:
			fp.write( "%d %s\n" % (level, item[0]))
			for item in item[2]:
				self._WriteContentsHelper(item, level+1, fp)

################################################################
#
# Help Project Manager
#
################################################################
class HelpProjectManager:
	def __init__(self, docPrefix, rtfPrefix, trace):
		# misc config params

		self.trace = trace
		self.projectDirectory = projectDirectory
		
		self.docPrefix = docPrefix
		self.rtfPrefix = rtfPrefix[:4]
		fnPrefix=os.path.join(projectDirectory, self.rtfPrefix)
		for filename in glob.glob(fnPrefix+"*.rtf"):
			os.unlink(filename)
		try:
			fnPrefix=os.path.join(projectDirectory, self.docPrefix)
			os.unlink(fnPrefix+".hpj")
			os.unlink(fnPrefix+".hlp")
			os.unlink(fnPrefix+".cnt")
		except os.error:
			pass

		self.docCounter = 0
		self.unresName = None
		self.hpjName = None
		self.contents = None
		self.title = None
		self.ResetButtons()
		self.baseHRef = None
		self.hrm = HRefManager(self.ShowProgressMessage)
		self.contentsBuilder = ContentsBuilder()

	def __print__(self):
		res="HelpProjectManager: projectDir=%s, docPrefix=%s, rtfPrefix=%s " % (self.projectDirectory, self.docPrefix, self.rtfPrefix)
		return res
	def __del__(self):
		Trace("Project Manager died", 3)
	def close(self):
		Trace("Project manager closed")
		self.hrm.close()
		self.hrm = None
		
	def ShowProgressMessage(self, msg = None):
		"Show a message, plus the count of documents done/remaining"
		noHRefs = self.hrm.GetNumHRefs()
		noProc = self.hrm.GetNumHRefsProcessed()
		if msg is None:
			if self.baseHRef is None:
				msg = "Processing"
			else:
				msg = "Processing %s" % self.baseHRef.href
		win32ui.SetStatusText("%s - completed %d of %d - %d remain" % (msg,noProc,noHRefs,noHRefs-noProc),1)
		
	def ResetButtons(self):
		# Key used here is the html text used to id a partic button
		self.buttons = {}
		self.buttons["up"] = "btn_up", "&Up", None
		self.buttons["prev"] = "btn_prev", "&Prev", None
		self.buttons["next"] = "btn_next", "&Next", None
		self.buttons["index"] = "btn_top", "&Top", None
#		self.buttons["contents"] = "btn_contents", "&Contents", self.contents

	def Build(self, href):
		Trace("Started preprocessing files on %s" % (time.ctime(time.time())),0)
		self.hrm.AddHRef(href)
		num = 0
		maxHRefs = 99999
#		maxHRefs = 15
		while num<maxHRefs:
			refStr = self.hrm.GetFirstUnprocessedRef()
			if refStr is None:
				break
			self.ProcessHTMLRef(refStr)
			self.contentsBuilder.CheckBestContents()
			num = num + 1
#		self.hrm.Dump()
		self.BuildRTFFiles()
		self.BuildHPJ()
		self.BuildHLP()
	def BuildRTFFiles( self ):
		# build a list of all base hrefs.
		baseHRefs = self.hrm.GetBaseHRefList(HRefManager.STATUS_PROCESSED)
		self.wordSession = WordSession()
		try:
			Trace("Started building RTF files on %s" % (time.ctime(time.time())),0)
			total = len(baseHRefs)
			num = 0
			for hrefOb in baseHRefs:
				num = num + 1
				data = self.OpenHRef(hrefOb)
				if data is None: continue

				wb = self.wordSession.GetWordBasicObject()
				win32ui.SetStatusText("Processing document %d of %d - %d remain." % (num, total, total-num),1)
				writer = WriterForGeneration(self, wb)
				p = ParserForGeneration(self, writer, hrefOb )
				self.ProcessWordDocument(hrefOb, p, data)
				writer.close()
				p.close()	# close the parser

			self.BuildUnresolvedDocument()

		finally:
			self.wordSession.close()
			Trace("Finished on %s " % time.ctime(time.time()),0)

	def OpenHRef(self, href):
		try:
			f = urllib.urlopen(href.href)
			data = f.read()
			self.baseHRef = href
			f.close()
		except IOError, details:
#			Trace("*** Could not open href '%s'\n%s" % (href, details))
			href.SetStatus(HRefManager.STATUS_ERROR, details)
			return None
		return data
		
	def ProcessHTMLRef( self, href ):
		hrefOb = self.hrm.AddHRef(href)
#		hrefOb = self.hrm.GetHRefObject(href)
		status = hrefOb.GetStatus()
		if status==HRefManager.STATUS_PROCESSED:
			Trace("href '%s' already processed!" % href, 2)
			return 1
		if status!=HRefManager.STATUS_NONE:
			Trace("Skipping reference to '%s' - previous error" % href,2)
			return 0	# previously tried, so wont again.
		# Work out if we can process the reference
		Trace("Attempting to process href '%s'" % href, 1)
		self.ShowProgressMessage("Processing %s" % (href))
		host = urlparse.urlparse(href)[1]
		if host in validHosts:
			data = self.OpenHRef(hrefOb)
			if data is None: return
		else:
			hrefOb.SetStatus(HRefManager.STATUS_ERROR, "The host was excluded from the build")
			return

		writer = WriterForPreprocessing(self.contentsBuilder)
		p = ParserForPreprocessing(self, writer, hrefOb)
		p.feed(data)
		writer.close()
		if self.title is None and not p.title is None:
			title = MakeKeyword(p.title)
			self.title = string.upper(title[0]) + title[1:]

		self.hrm.SetHRefStatus( href, HRefManager.STATUS_PROCESSED)
		p.close()	# close the parser
#		self.baseHRef = None

	def ProcessWordDocument( self, href, p, data ):
		fileName = os.path.join(self.projectDirectory, "%s%04d" % (self.rtfPrefix, self.docCounter))
		self.docCounter = self.docCounter + 1
		
		self.wordSession.CreateWordDocument(href.context)
		p.feed(data)
		self.wordSession.FinishWordDocument(fileName, p.title, self.buttons)

	def BuildUnresolvedDocument(self):
		self.wordSession.CreateWordDocument("Unresolveds")
		# first just show a list of all items.
		wb = self.wordSession.GetWordBasicObject()
		wb.Insert("The following references where not loaded when creating this help file")
		errorHRefs =  self.hrm.GetBaseHRefList(HRefManager.STATUS_ERROR)
		
		for href in errorHRefs:
			win32ui.PumpWaitingMessages()
			wb.Insert(chr(11)+href.href)
		wb.InsertPara()
		wb.InsertBreak(0)
		total = len(errorHRefs)
		thisnum = 0
		for href in errorHRefs:
			win32ui.PumpWaitingMessages()
			thisnum = thisnum + 1
			win32ui.SetStatusText("Processing unresolved %d of %d - %d remain" %(thisnum,total, total-thisnum), 1)
			status = href.GetStatus()
			context = href.GetContext()
			if status!=HRefManager.STATUS_PROCESSED:
				self.wordSession.InsertFootnoteText("#", context)
				wb.EndOfLine()
				self.wordSession.InsertFootnoteText("$", "Unresolved reference: %s" % href.href )
				butStrs = []
				for id, dummy_text, dummy_context in self.buttons.values():
					butStrs.append('DB("%s")' % id)
				if len(butStrs)>0:
					self.wordSession.InsertFootnoteText("!", string.joinfields(butStrs, ';') )
				wb.Style("H1")
				wb.Insert("Unavailable reference...")
				wb.InsertPara()
#				wb.ResetChar._proc_()
				wb.Style("Normal")
				wb.Insert("The reference ")
				wb.Font("Courier New")
				wb.Insert(href.href)
				wb.ResetChar._proc_()
				wb.Insert(" was not included in this help file"+chr(11))
				wb.Insert._proc_("Details: %s" % (`href.msg`) )
				wb.InsertPara()
				wb.InsertBreak(0)
				
		self.unresName = os.path.join(self.projectDirectory, "%sures" % (self.rtfPrefix))
		self.wordSession.FinishWordDocument(self.unresName, "Unresolved Jumps", self.buttons)
	def BuildHLP(self):
		try:
			import win32api
			win32api.ShellExecute(0,None, "%s.hpj" % os.path.join(self.projectDirectory, self.docPrefix), None, None, 1)
		except:
			pass
	
	def BuildHPJ(self):
		cntFileName = self.WriteContentsData()
		fileName = os.path.join(self.projectDirectory, "%s.hpj" % (self.docPrefix))
		Trace("Writing HPJ file %s"%fileName, 0)
		f = open( fileName, "wt" )
		try:
			f.write ("; ************************************************************************\n;\n")
			f.write ("; Help project file generated from HTML sources!\n")
			f.write ("; Created %s\n;\n" % (time.ctime(time.time())))
			f.write ("; ************************************************************************\n\n\n")
			f.write ("[OPTIONS]\n")
			if self.title:
				f.write ("title = %s\n" % self.title)
			f.write ("compress = 1\nwarning = 3\noldkeyphrase=0\nreport=No\n")
	#		if self.contents:
	#			f.write ("contents=%s\n"%self.hrm.GetHRefsContextString(self.contents))
			if cntFileName:
				f.write ("cnt=%s\n"% os.path.split(cntFileName)[1])
			f.write ("\n")
			f.write ("[CONFIG]\n")
			# need to write out dummy jump locations for the buttons.
			for id, text, context in self.buttons.values():
				if id != 'btn_contents':
					f.write ('CreateButton("%s", "%s", "JumpContents(`\')")\n' % (id, text))
			f.write ("\n")
			
			f.write ("[FILES]\n")
			for docNo in range(self.docCounter):
				f.write ("%s%04d.rtf\n" % (self.rtfPrefix, docNo))
			if self.unresName:
				f.write ("%s.rtf\n" % self.unresName)
			f.write ("\n")
		finally:
			f.close()
		self.hpjName = fileName
		Trace("HPJ file written", 0)

	def WriteContentsData(self):
		if not self.contentsBuilder.HaveContentsData():
			return None
		fileName = os.path.join(self.projectDirectory, "%s.cnt" % (self.docPrefix))
		fp=open(fileName , "w")
		try:
			fp.write(":Base %s.hlp>main\n" % self.docPrefix)
			self.contentsBuilder.WriteContentsData(self.title, fp)
		finally:
			fp.close()
		import win32api
		try:
			win32api.ShellExecute(0,None, fileName, None, None, 1)
		except:
			pass
		return fileName

	def BuildHLP(self):
		import win32api
		win32api.ShellExecute(0,None, "%s.hpj" % os.path.join(self.projectDirectory, self.docPrefix), None, None, 1)
		
#	def RunHLP(self):
#		import win32api
#		win32api.ShellExecute(0,None, "%s.hlp" % os.path.join(self.projectDirectory, self.docPrefix), None, None, 1)


################################################################
#
# The Word Formatter - basically nothing!
#
################################################################
WFParent=formatter.AbstractFormatter
class WordFormatter(WFParent):
	def __init__(self, writer):
		WFParent.__init__(self, writer)
		self.blanklines = 1
	def close(self):
		Trace("Formatter closing",2)
		self.d = None
		self.b = None

################################################################
#
# The writer and parser for the preprocessing stage.
#
################################################################
W4PParent=formatter.AbstractWriter
class WriterForPreprocessing(W4PParent):
	def __init__(self, contentsBuilder):
		self.contentsBuilder = contentsBuilder
		self.emitToContents = 0
		self.emitData = None
		W4PParent.__init__ (self)
	def __del__(self):
		Trace("Preprocessor Writer dieing",3)
	def close(self):
		Trace("Preprocessor Writer closing",3)
		self.contentsBuilder = self.emitData = None
	def new_font(self, font): pass
	def new_margin(self, margin, level): pass
	def new_spacing(self, spacing): pass
	def new_styles(self, styles): pass
	def send_paragraph(self, blankline): pass
	def send_line_break(self): pass
	def send_hor_rule(self): pass
	def send_label_data(self, data): pass
	def send_literal_data(self, data): pass

	def send_flowing_data(self, data):
		self.CheckEmitToContents(data)
		win32ui.PumpWaitingMessages()
	def CheckEmitToContents(self, data):
		if self.emitToContents:
			self.emitData = self.emitData + data
	def StartEmitToContents(self, level):
		self.emitToContents = 1
		self.emitLevel = level
		self.emitData = ''
	def FinishEmitToContents(self, context):
		if not self.emitToContents: return
		ob = self.contentsBuilder.contentsRoot
		if ob is None: return
		for level in range(self.emitLevel-1):
			ob = ob[2][len(ob[2])-1]
		ob[2].append((self.emitData, context, []))
		self.emitToContents = 0
#
# The Parser
#
WP4PParent=htmllib.HTMLParser
class ParserForPreprocessing(WP4PParent):
	def __init__(self, pm, writer, href):
		self.contentsTreeLevel = None
		self.pm = pm
		self.formatter = WordFormatter(writer)
		self.hrefBase = href
		WP4PParent.__init__(self, self.formatter)
	def __del__(self):
		Trace("ProcessorParser died",3)
		
	def close(self):
		Trace("ProcessorParser closed",3)
		WP4PParent.close(self)
		if self.formatter:
			self.formatter.close()
		self.formatter = self.pm = self.hrefBase = None

	def anchor_bgn(self, href, name, type):
		WP4PParent.anchor_bgn(self, href, name, type)
		self.anchorcontext = None
		self.anchorname = name
		if len(name) > 0:
			# This means this anchor has a valid location ID.
			# Assume name is a sub-document reference only.
			fullRef = "%s#%s" %(os.path.split(self.hrefBase.href)[1], self.anchorname)
			# Indicate this is a valid reference.
			context = self.pm.hrm.AddHRef( fullRef, HRefManager.STATUS_PROCESSED )
		if len(href) > 0:
			if href[0] == '#':
				fullRef = "%s%s" %(os.path.split(self.hrefBase.href)[1], href)
			else:
				fullRef = href
			# This is a jump to the location.  Indicate we need it.
			context = self.pm.hrm.AddHRef( fullRef )
			if not self.contentsTreeLevel is None:
				self.anchorcontext = self.pm.hrm.AddHRef( href )
				self.formatter.writer.StartEmitToContents(self.contentsTreeLevel)

	def anchor_end(self):
		if self.anchor:
			if self.anchorcontext:
				self.formatter.writer.FinishEmitToContents(self.anchorcontext)
			self.anchor = None
		self.inanchor = 0
	def do_li(self, attrs):
		self.contentsTreeLevel = len(self.list_stack) #+ self.headingLevel
#		print "do li - attrs are %s, indent is %d" %(`attrs`,)
		WPParent.do_li(self, attrs)
		
	def end_ul(self):
		WPParent.end_ul(self)
		self.contentsTreeLevel = None

	def start_h1(self, attrs):
		WP4PParent.start_h1(self, attrs)
		self.save_bgn()

	def start_h2(self, attrs):
		WP4PParent.start_h2(self, attrs)
		self.save_bgn()

	def start_h3(self, attrs):
		WP4PParent.start_h3(self, attrs)
		self.save_bgn()
	
	def common_endh(self):
		try:
			data = self.save_end()
		except:
			print "Error in href ", self.hrefBase.href
			raise error
		self.pm.contentsBuilder.AddHeading(data, self.pm.hrm.GetHRefObject( self.hrefBase.href) )
		self.handle_data(data)
		
	def end_h1(self): 
		self.common_endh()
		WP4PParent.end_h1(self)
	def end_h2(self): 
		self.common_endh()
		WP4PParent.end_h2(self)
	def end_h3(self): 
		self.common_endh()
		WP4PParent.end_h3(self)

################################################################
#
# The writer and parser for the Generation process.
#
################################################################

styles = { \
	'h1' : ('H1',1),	\
	'h2' : ('H2',1),	\
	'h3' : ('H3',1), \
	'jt' : ('Jump Text',1), \
	'jl' : ('Jump Loc',1), \
	'pt' : ('Popup Text',1)}

W4GParent=formatter.AbstractWriter
class WriterForGeneration(W4GParent):
	def __init__(self, pm, wb):
		self.wb = wb
		self.pm = pm
		W4GParent.__init__ (self)
	def __del__(self):
		Trace("Backend dieing",3)
	def close(self):
		Trace("Backend closing",3)
		self.wb = self.pm = None
	def new_font(self, font):
		self.SetWordFont(font)
	def new_margin(self, margin, level):
		try:
			self.wb.FormatParagraph._proc_("%dcm"%level)
		except oleauto.ole_error:
			print "Error - could not set left margin to level %d" % level
	def new_spacing(self, spacing):
		print "new_spacing(%s)" % `spacing`
	def new_styles(self, styles):
		print "new_styles(%s)" % `styles`
	def send_paragraph(self, blankline):
		self.wb.InsertPara._proc_()
		self.wb.ResetChar._proc_()
		self.wb.ResetPara._proc_()
		
	def send_line_break(self):
		self.wb.Insert._proc_(chr(11))
	def send_hor_rule(self):
		pass

	def send_label_data(self, data):
		if data=='*':
			self.wb.InsertSymbol("Symbol", 0, "183")
			self.wb.Insert._proc_(' ')
#			self.wb.FormatBulletDefault._proc_(1)
		else:
			print "send_label_data(%s)" % `data`

	def send_flowing_data(self, data):
		self.wb.Insert._proc_(data)
		win32ui.PumpWaitingMessages()

	def send_literal_data(self, data):
		self.wb.Insert._proc_(data)
		win32ui.PumpWaitingMessages()

	def SetWordFont( self, font ):
		if font is None:
			self.wb.ResetChar._proc_()
#			self.wb.ResetPara._proc_()
#			self.wb.NormalStyle._proc_()
			return

		face, i, b, tt = font
		if not face is None:
			try:
				styleName, type = styles[face]
				self.wb.FormatStyle._proc_(styleName, 0, 0, "", "", "", type)
			except KeyError:
				print "Unknown font - %s - ignored " % `face`
		if not i is None:
			self.wb.Italic._proc_(i)
		if not b is None:
			self.wb.Bold._proc_(b)
		if tt:
			self.wb.FormatFont._proc_("",0,0,0,0,0,0,0,0,0,0,0,"",0,0,"Courier New")

WPParent=htmllib.HTMLParser
class ParserForGeneration(WPParent):
	def __init__(self, pm, writer, baseHRef):
		self.pm = pm
		self.baseHRef = baseHRef
		self.formatter = WordFormatter(writer)
		WPParent.__init__(self, self.formatter)
		self.bHaveHead = 0
		self.buttonName = None
#		self.locNext = self.locPrev = self.locContents = self.locUp = None
	def __del__(self):
		Trace("Parser died",3)
		
	def close(self):
		Trace("Parser closed",3)
		WPParent.close(self)
		if self.formatter:
			self.formatter.close()
		self.formatter = self.pm = self.baseHRef = None
		
	def addkeyword(self, keyword):
		keyword = string.strip(keyword)
		if not keyword:
			return
		self.pm.wordSession.InsertFootnoteText("K", ';%s'%keyword)
		
	def anchor_bgn(self, href, name, type):
		WPParent.anchor_bgn(self, href, name, type)
		self.anchorcontext = None
		self.anchorname = name
		if len(name) > 0:	# Assume name is a sub-document reference only.
			fullRef = "%s#%s" %(os.path.split(self.baseHRef.href)[1], self.anchorname)
			ob = self.pm.hrm.GetHRefObject( fullRef )
			self.pm.wordSession.wb.ResetChar._proc_()
			self.pm.wordSession.InsertFootnoteText("#", ob.context)
		if len(href) > 0:
			if href[0] == '#':
				fullRef = "%s%s" %(os.path.split(self.baseHRef.href)[1], href)
			else:
				fullRef = href
			ob = self.pm.hrm.GetHRefObject( fullRef )
			if ob.status==HRefManager.STATUS_ERROR:
				self.formatter.push_font(('pt', None, None, None))
			else:
				self.formatter.push_font(('jt', None, None, None))
#		if not type in ["", "menu"]:
#			self.buttonName = type

	def anchor_end(self):
		if self.anchor:
			self.anchor = None
			pos=len(self.anchorlist)-1
			anchor = self.anchorlist[pos]
			# set the font to the jump location formatting
			if len(anchor)>0:
				self.formatter.pop_font()
				self.formatter.push_font(('jl', None, None, None))
				if anchor[0] == '#':
					anchor = "%s%s" %(os.path.split(self.baseHRef.href)[1], anchor)
				context = self.pm.hrm.GetHRefObject(anchor).context
				self.handle_data( context )
				self.formatter.pop_font()
			
#				if self.buttonName and self.pm.buttons.has_key(self.buttonName):
#					id, text, href = self.pm.buttons[self.buttonName]
#					self.pm.buttons[self.buttonName] = id, text, context
#				self.buttonName=None

		self.inanchor = 0

	# support multiple levels of UL (Unstructured List!)
	def start_h1(self, attrs):
		WPParent.start_h1(self, attrs)
		self.save_bgn()
	def start_h2(self, attrs):
		WPParent.start_h2(self, attrs)
		self.save_bgn()
	def start_h3(self, attrs):
		WPParent.start_h3(self, attrs)
		self.save_bgn()
	def start_h4(self, attrs):
		WPParent.start_h4(self, attrs)
		self.save_bgn()
	def start_h5(self, attrs):
		WPParent.start_h5(self, attrs)
		self.save_bgn()
	def start_h6(self, attrs):
		WPParent.start_h6(self, attrs)
		self.save_bgn()
		
	def do_end_h(self,parent):
		data = self.save_end()
		self.handle_data(data)
		keyword = MakeKeyword(data)
		if keyword:
			self.addkeyword(keyword)
		parent(self)
		
	def end_h1(self): 
		self.do_end_h(WPParent.end_h1)
	def end_h2(self): self.do_end_h(WPParent.end_h2)
	def end_h3(self): self.do_end_h(WPParent.end_h3)
	def end_h4(self): self.do_end_h(WPParent.end_h4)
	def end_h5(self): self.do_end_h(WPParent.end_h5)
	def end_h6(self): self.do_end_h(WPParent.end_h6)

	def start_head(self, attrs):
		self.bHaveHead = 1
		WPParent.start_head(self, attrs)

	def handle_comment(self, data):
		Trace("Handle comment called!",9)
		pass
		
	def start_meta(self, attrs):
		meta_name = meta_value = None
		for attrname, value in attrs:
			if attrname == 'name':
				meta_name = value
			if attrname == 'value':
				meta_value = value
		if meta_name and meta_value:
			if meta_name == "keywords":
				self.addkeyword(meta_value)
	def end_meta(self):
		pass

	def do_img(self, attrs):
		for attrname, value in attrs:
			if attrname=="alt":
				self.buttonName = value
				self.handle_data(value)
				Trace("do_img using alt button '%s'" % (value), 2)
				return
		WPParent.do_img(self, attrs)
							
def BuildHelpFile(localDir, href, docPrefix, rtfPrefix):
	oldDir = os.getcwd()
	if localDir: os.chdir(localDir)
	try:
		p = HelpProjectManager(docPrefix, rtfPrefix, trace)
		try:
#			p.BuildRTFFiles(os.path.split(href)[1])
			p.Build(href)
#			p.BuildHPJ()
#			if doBuild:
#				p.BuildHLP()
#				if doRun:
#					p.RunHLP()
		except KeyboardInterrupt:
			Trace("*** Interrupted")
		p.close()
	finally:
		pass
		os.chdir(oldDir)
	return p

def Bld(localDir, href, docPrefix, rtfPrefix):
	import traceback
	try:
		BuildHelpFile(localDir, href, docPrefix, rtfPrefix)
	except:
		traceback.print_tb(sys.exc_traceback)
		print sys.exc_type, ":", sys.exc_value
		print "Building %s failed!" % href 

targets= {
	'test':("c:/temp", "test.html", "test", "test"),
	'tut':("d:/users/public/html/python/tut", "tut.html", "py-tut", "pytu"),
	'lib':("d:/users/public/html/python/lib", "top.html", "py-lib", "pyli"),
	'ext':("d:/users/public/html/python/ext", "ext.html", "py-ext", "pyex"),
	'ref':("d:/users/public/html/python/ref", "ref.html", "py-ref", "pyre"),
	'html-spec':("d:/users/public/html/html-spec", "html-spec_toc.html", "html2", "html")
	}

def bld():
	apply(Bld, targets['tut'])
	apply(Bld, targets['ext'])
	apply(Bld, targets['ref'])
	apply(Bld, targets['lib'])
#	apply(Bld, targets['html-spec'])


def test():
	return apply(BuildHelpFile, targets['test'])

def newtest():
    import sys
    file = 'd:\\users\\public\\html\\python-tut\\tut.html'
    if sys.argv[1:]: file = sys.argv[1]
    fp = open(file, 'r')
    data = fp.read()
    fp.close()
    from formatter import DumbWriter, AbstractFormatter
    from htmllib import HTMLParser
    w = DumbWriter()
    f = AbstractFormatter(w)
    p = HTMLParser(f)
    p.feed(data)
    p.close()

