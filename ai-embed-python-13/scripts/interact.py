##################################################################
#
#	Interactive Script parser and executer
#

#from main import app
import app
import sys
import string
import regex
import regsub
import __main__

import win32ui
# import my DLL extension modules.
import win32api
import win32con
import winout

sectionProfile = "Interactive Window"
valueFormatTitle = "FormatTitle"
valueFormatInput = "FormatInput"
valueFormatOutput = "FormatOutput"
valueFormatOutputError = "FormatOutputError"

formatTitle = (-536870897, 0, 220, 0, 16711680, 184, 34, 'Arial')
formatInput =  (-402653169, 0, 200, 0, 0, 0, 49, 'Courier')
formatOutput =  (-402653169, 0, 200, 0, 8421376, 0, 49, 'Courier')
formatOutputError = (-402653169, 0, 200, 0, 255, 0, 49, 'Courier')

# couple of exceptions defined for this module
excNoValidCommand = 'No Valid Command'
excEmptyCommand = 'Empty Command'
excContinueCommand = 'Continue Command'

class flags:
	trace=0					# tracing or not.
	# queueing of output.
	WQ_NONE = 0
	WQ_LINE = 1
	WQ_IDLE = 2

#
# Define my Window classes
#
window_exc='window'


def LoadFontPreferences():
	global formatTitle, formatInput, formatOutput, formatOutputError
	try:
		fmt = win32ui.GetProfileVal( sectionProfile, valueFormatTitle, "" )
		if len(fmt): formatTitle = eval(fmt)
		fmt = win32ui.GetProfileVal( sectionProfile, valueFormatInput, "" )
		if len(fmt): formatInput = eval(fmt)
		fmt = win32ui.GetProfileVal( sectionProfile, valueFormatOutput, "" )
		if len(fmt): formatOutput = eval(fmt)
		fmt = win32ui.GetProfileVal( sectionProfile, valueFormatOutputError, "" )
		if len(fmt): formatOutputError = eval(fmt)
	except:
		win32ui.MessageBox("The Font Preferences could not be loaded")

def SaveFontPreferences():
	win32ui.WriteProfileVal( sectionProfile, valueFormatTitle, str(formatTitle) )
	win32ui.WriteProfileVal( sectionProfile, valueFormatInput, str(formatInput) )
	win32ui.WriteProfileVal( sectionProfile, valueFormatOutput, str(formatOutput) )
	win32ui.WriteProfileVal( sectionProfile, valueFormatOutputError, str(formatOutputError) )

###############################################################
#
# This class handles the Python interactive interpreter.
#
# It uses a basic EditWindow, and does all the magic.
# This is triggered by the enter key hander attached by the
# start-up code.  It determines if a command is to be executed
# or continued (ie, emit "... ") by snooping around the current
# line, looking for the prompts
#

class InteractiveView(winout.WindowOutputView):
	def __init__(self,  doc):
		LoadFontPreferences()
		winout.WindowOutputView.__init__(self, doc)
		self.SetWordWrap(win32ui.CRichEditView_WrapNone)
		# Create the prompts
		try:
			sys.ps1
		except AttributeError:
			sys.ps1 = '>>> '
			sys.ps2 = '... '
	def DoGetLine(self, line=-1):
		if line==-1: line = self.LineFromChar()
		str = self.GetLine(line)
		while len(str) and str[-1] in ['\n','\r']:
			str = str[:-1]
		return str
	def AppendToPrompt(self,bufLines):
		" Take a command and stick it at the end of the buffer (with python prompts inserted if required)."
		lastLineNo = self.GetLineCount()-1
		line = self.DoGetLine(lastLineNo)
		if (line!=sys.ps1):
			if len(line)!=0:
				self.write('\n')
			self.DrawPrompt()
		pos = 0
		for bufLine in bufLines[:-1]:
			if regex.match('[ \t]*$', bufLine)==-1:
				self.write( bufLine + '\n' )
				self.DrawPrompt(sys.ps2)
		if regex.match('[ \t]*$', bufLines[-1])==-1:
			self.write(bufLines[-1])
		self.flush()

	def DrawPrompt(self, * prompt):
		# if param is given, it is a tuple
		self.flush()
		self.SetSelectionCharFormat(formatInput)
		outputMethod = self.write
		if len(prompt)==0:
			outputMethod(sys.ps1)
		else:
			outputMethod(prompt[0])

	def HookHandlers(self):
		winout.WindowOutputView.HookHandlers(self)
		self.HookKeyStroke(self.keyhandler_enter,13)
		self.HookKeyStroke(self.keyhandler_esc,27)
		# Hook menu command (executed when a menu item with that ID is selected from a menu/toolbar
		self.HookCommand(self.OnSelectBlock, win32ui.ID_EDIT_SELECT_BLOCK)
		self.HookCommand(self.OnFormatInput, 5000)
		self.HookCommand(self.OnFormatOutput, 5001)
		self.HookCommand(self.OnFormatError, 5002)
		self.HookCommand(self.OnFormatTitle, 5003)

	def GetRightMenuItems(self):
		# Just override parents
		flags=win32con.MF_STRING|win32con.MF_ENABLED
		subMenu = win32ui.CreatePopupMenu()
		subMenu.AppendMenu(flags, 5000, "&Input text...")
		subMenu.AppendMenu(flags, 5001, "&Output text...")
		subMenu.AppendMenu(flags, 5002, "&Error text...")
		subMenu.AppendMenu(flags, 5003, "&Title text...")

		ret = []
		ret.append(flags|win32con.MF_POPUP, subMenu.GetHandle(), "&Format")
		ret.append(flags, win32ui.ID_EDIT_UNDO, '&Undo')
		ret.append(win32con.MF_SEPARATOR);
		ret.append(flags, win32ui.ID_EDIT_CUT, 'Cu&t')
		ret.append(flags, win32ui.ID_EDIT_COPY, '&Copy')
		ret.append(flags, win32ui.ID_EDIT_PASTE, '&Paste')
		ret.append(win32con.MF_SEPARATOR)
		ret.append(flags, win32ui.ID_EDIT_SELECT_ALL, '&Select all')
		ret.append(flags, win32ui.ID_EDIT_SELECT_BLOCK, 'Select &block')
		return ret

	# GetBlockBoundary takes a line number, and will return the
	# start and and line numbers of the block, and a flag indicating if the
	# block is a Python code block.
	# If the line specified has a Python prompt, then the lines are parsed
	# backwards and forwards, and the flag is true.
	# If the line does not start with a prompt, the block is searched forward
	# and backward until a prompt _is_ found, and all lines in between without
	# prompts are returned, and the flag is false.
	def BuildPromptPat(self):
		useps1 = regsub.gsub('\\.', '\\\\.', sys.ps1)
		useps2 = regsub.gsub('\\.', '\\\\.', sys.ps2)
		self.promptPat = regex.compile('\\(\\(' + useps1 + '\\)\\|\\(' + useps2 + '\\)\\)')

	# This will return a tuple giving the boundary of the current "block".  A block
	# is either a code block, or a non code block, and is determined by searching
	# around the current line for a prompt/prompt change.
	def GetBlockBoundary( self, lineNo ):
		line = self.DoGetLine(lineNo)
		maxLineNo = self.GetLineCount()-1
		self.BuildPromptPat()
		if (self.promptPat.match(line)==-1):				# Non code block
			flag = 0
			startLineNo = lineNo
			while startLineNo>0:
				if self.promptPat.match(self.DoGetLine(startLineNo-1))!=-1:
					break;	# there _is_ a prompt
				startLineNo = startLineNo-1
			endLineNo = lineNo
			while endLineNo<maxLineNo:
				if self.promptPat.match(self.DoGetLine(endLineNo+1))!=-1:
					break;	# there _is_ a prompt
				endLineNo = endLineNo+1
		else:												# Code block
			flag = 1
			startLineNo = lineNo
			while startLineNo>0 and self.promptPat.group(1)!=sys.ps1:
				if self.promptPat.match(self.DoGetLine(startLineNo-1))==-1:
					break;	# there is no prompt.
				startLineNo = startLineNo - 1
			endLineNo = lineNo
			while endLineNo<maxLineNo:
				if self.promptPat.match(self.DoGetLine(endLineNo+1))==-1:
					break	# there is no prompt
				if self.promptPat.group(1)==sys.ps1:
					break	# this is another command
				endLineNo = endLineNo+1
				# continue until end of buffer, or no prompt
		return (startLineNo, endLineNo, flag)

	def ExtractCommand( self, lines ):
		start, end, lineNo = lines
		curLine = self.DoGetLine(lineNo)
		# trim comment and leading while space
		#commentPat = regex.compile('[ \t]*#.*$')
		#curLine = regsub.gsub(commentPat,'', curLine)
		promptLen = self.promptPat.match(curLine)
		curLine=curLine[promptLen:]
		if promptLen==-1:		# make a check for something that cant happen :-)
			raise window_exc, "interact.CInteractivePython.ExtractCommand: Internal error - cant refind prompt!!"
		retList = []
		while end >= start:
			thisLine = self.DoGetLine(end)
			promptLen = self.promptPat.match(thisLine)
			retList = [thisLine[promptLen:]] + retList
			end = end-1
		return retList
	
	###################################
	#
	# Message/Command/Key Hooks.
	#
	# Enter key handler
	#
	def keyhandler_enter(self, key):
		# First, check for an error message
		if self.JumpToErrorLine(): return 0
		lineNo = self.LineFromChar()
		try:
			if win32api.GetKeyState(win32con.VK_SHIFT)<0:
				self.write('\n')
				raise excContinueCommand
			start, end, isCode = self.GetBlockBoundary(lineNo)
			if isCode==0:
				if flags.trace:
					print "raise excNoValidCommand as isCode==0"
				raise excNoValidCommand
			lines = self.ExtractCommand((start,end,lineNo))

			if (end!=self.GetLineCount()-1):
				# Not at end of buffer - copy to end, and get ready to execute.
				win32ui.SetStatusText('Press ENTER to execute command')
				self.AppendToPrompt(lines)
				return 0;	# just copy to the end.

			if len(lines)==0:
				if flags.trace:
					print "raise excEmptyCommand as len(lines)==0"
				raise excEmptyCommand

			curLine = lines[lineNo-start]
			# Now see what we can so with the command.  We...
			# attempt a compile('exec').  A syntax Error - EOF means "need more of a command"
			# Any other syntax error means a real syntax error, and we report this.
			# Then, we go for a compile with the 'eval' flag.  A syntax error here means
			# that it must be an expression, so will be exec'd.  Otherwise, it will be eval'd
			
			# This is done to emulate the behaviour of the Python interpreter at a console
			# and saves trying to double-guess Python, wrt syntax etc.
			# However, do need to perform a leading whitespace check, to handle 2 lines same indent.
			self.template.OutputGrab()	# grab the output for the command exec.
			print

			if len(string.split(curLine))>0 and string.find(string.whitespace, curLine[0])<>-1:	# check for leading whitespace
				raise excContinueCommand
			try:
				cmd = string.joinfields(lines,'\n')+'\n'
				codeObj = compile(cmd,'<interactive input>','exec')
			except SyntaxError, details:
				message = details[0]
				if message=='unexpected EOF while parsing':
					raise excContinueCommand
				# re-raise the error, for the error printing to be done.
				raise SyntaxError, details
			try:
				codeObj = compile(cmd,'<interactive input>','eval')
				# worked - eval it
				ret = eval(codeObj , __main__.__dict__)
				if ret!=None:
					print repr(ret)
				win32ui.SetStatusText('Successfully evaluated expression')
			except SyntaxError: # means bad syntax for eval, but exec is OK
				exec codeObj in __main__.__dict__
				win32ui.SetStatusText('Successfully executed statement')
		# First grab the errors that I generate, or handle specially.
		except excContinueCommand:
			win32ui.SetStatusText('Ready for rest of command')
			self.DrawPrompt(sys.ps2)
			
			curLine = self.DoGetLine(lineNo)
			pat = regex.compile('\([ \t]*\)[~ \t]')
			if pat.match(curLine)>0 and pat.group(1) <> None:
				print pat.group(1),
			else:
				print '\t',
			self.flush()
			self.template.OutputRelease()
			return 0

		except (excEmptyCommand,excNoValidCommand):
			# draw a new prompt.
			if flags.trace:
				print "Empty/Invalid command exception"
			win32ui.SetStatusText('Ready')
			print
			self.DrawPrompt()
			self.flush()
			self.template.OutputRelease() # these exceptions occur before output grabbing, but that's OK
			return 0
			
		except : # Grab all errors
			# firstly, grab all the exception values I need, so any exceptions
			# raised by me in this code dont mess things up.
			exc_type = sys.exc_type
			exc_value = sys.exc_value
			exc_traceback = sys.exc_traceback
			if (flags.trace):
				print "Handling a general exception"
			filename = errno = None	# flags!
			if exc_type is SyntaxError:
				try:
					message, (filename, lineno, offset, text) = exc_value
					if not type(lineno)==type(0) or not type(offset)==type(0):
						filename = None	# reset flag - Cant trust this to be a valid error spec.
						message = str(exc_value)
				except:
					message = str(exc_value)
			else:
				try:
					errno, message = exc_value
				except:
					message = str(exc_value)

			# work with next traceback object, to avoid printing this line/file no
			self.flush()
			self.SetSelectionCharFormat(formatOutputError)
			import traceback
			traceback.print_exception(exc_type, exc_value, exc_traceback.tb_next)
			#win32ui.PrintTraceback(exc_traceback.tb_next,sys.stderr)
			if exc_type is SyntaxError and not filename is None:
#				print '  File "'+ filename+  '", line '+ repr(lineno)
#				# create the '^' indicator - must handle tab characters.
#				leader=''
#				for col in range(0,offset-2):
#					if text[col]=='\t' : leader = leader + '\t'
#					else: leader = leader+' '
#				print ' '*(len(sys.ps1)), text,
#				print ' '*(len(sys.ps1)), leader, "^"
				statusText = exc_type+': '+str(message)
			elif not errno is None:
				statusText = exc_type+': Error '+str(errno)+': '+str(message)
			else:
				statusText = exc_type+': '+str(message)
			win32ui.SetStatusText(statusText)
#			print statusText
				
		self.DrawPrompt()
		self.flush() # write all pending output.
		self.template.OutputRelease()
		return 0

	# Test ESC key handler
	def keyhandler_esc(self, key):
		lineNo = self.LineFromChar()
		if flags.trace:
			print
		start, end, isCode = self.GetBlockBoundary(lineNo)
		if flags.trace:
			print 'Start :', start, ' End :', end, ' IsCode :', isCode
		startIndex = self.LineIndex(start)
		endIndex = self.LineIndex(end+1)-2	# skip \r + \n
		if endIndex<0:	# must be beyond end of buffer
			endIndex = -2	# self.Length() - no length function - this seems to work!
		if flags.trace:
			print 'Index - Start :', startIndex, ' End :', endIndex
		self.SetSel(startIndex,endIndex)
		return 1

	def OnSelectBlock(self,command, code):
		lineNo = self.LineFromChar()
		if flags.trace:
			print
		start, end, isCode = self.GetBlockBoundary(lineNo)
		if flags.trace:
			print 'Start :', start, ' End :', end, ' IsCode :', isCode
		startIndex = self.LineIndex(start)
		endIndex = self.LineIndex(end+1)-2	# skip \r + \n
		if endIndex<0:	# must be beyond end of buffer
			endIndex = -2	# self.Length()
		if flags.trace:
			print 'Index - Start :', startIndex, ' End :', endIndex
		self.SetSel(startIndex,endIndex)
	def GetFormat(self, fmt):
		dlg = win32ui.CreateFontDialog(fmt)
		if dlg.DoModal() <> win32con.IDOK: return None
		return dlg.GetCharFormat()
	def OnFormatTitle(self, command, code):
		global formatTitle
		fmt = self.GetFormat(formatTitle)
		if fmt:
			formatTitle = fmt
			SaveFontPreferences()
	def OnFormatInput(self, command, code):
		global formatInput
		fmt = self.GetFormat(formatInput)
		if fmt:
			formatInput = fmt
			SaveFontPreferences()
	def OnFormatOutput(self, command, code):
		global formatOutput
		fmt = self.GetFormat(formatOutput)
		if fmt:
			formatOutput = fmt
			SaveFontPreferences()
	def OnFormatError(self, command, code):
		global formatOutputError
		fmt = self.GetFormat(formatOutputError)
		if fmt:
			formatOutputError = fmt
			SaveFontPreferences()
	

class CInteractivePython(winout.WindowOutput):
	def __init__(self):
		winout.WindowOutput.__init__(self, sectionProfile, sectionProfile, \
		                             flags.WQ_IDLE, 1, None, None, None, InteractiveView )
		self.oldStdOut = self.oldStdErr = None
		self.OutputGrab()	# unmatched OutputRelease() - grabs default output.
		self.Create()
		vw = self.currentView
		vw.SetDefaultCharFormat(formatOutput)
		vw.SetSelectionCharFormat(formatTitle)
		self.write ("PythonWin %s\n%s\n" % (sys.version, sys.copyright) )
		self.write ("Portions copyright 1994-1996 Mark Hammond (MHammond@skippinet.com.au)\n")
		vw.DrawPrompt()
		vw.flush()
		                             
	def OutputGrab(self):
		if self.oldStdOut:
			self.oldStdOut = sys.stdout
		if self.oldStdErr:
			self.oldStdErr = sys.stderr
		sys.stdout=self
		sys.stderr=self
		try:
			self.flush()
			self.currentView.SetSelectionCharFormat(formatOutput)
		except:
			pass
	def OutputRelease(self):
		# a command may have overwritten these - only restore if not.
		if self.oldStdOut:
			if sys.stdout == self:
				sys.stdout=self.oldStdOut
		if self.oldStdErr:
			if sys.stderr == self:
				sys.stderr=self.oldStdErr
		self.oldStdOut = None
		self.oldStdErr = None
		self.flush()
		self.currentView.SetSelectionCharFormat(formatInput)

edit = CInteractivePython()
