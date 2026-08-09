import win32ui
import win32con
import win32api
import dyndlg
import string
import oleauto

FRAMEDLG_STD = win32con.DS_MODALFRAME | win32con.WS_POPUP | win32con.WS_CAPTION | win32con.WS_SYSMENU
SS_STD = win32con.WS_CHILD | win32con.WS_VISIBLE
BS_STD = SS_STD  | win32con.WS_TABSTOP
ES_STD = BS_STD | win32con.WS_BORDER
LBS_STD = ES_STD | win32con.LBS_NOTIFY | win32con.LBS_NOINTEGRALHEIGHT | win32con.WS_VSCROLL
CBS_STD = ES_STD | win32con.CBS_NOINTEGRALHEIGHT | win32con.WS_VSCROLL

typekindmap = {}
typekindmap[oleauto.TKIND_ENUM] = 'Enumeration'
typekindmap[oleauto.TKIND_RECORD] = 'Record'
typekindmap[oleauto.TKIND_MODULE] = 'Module'
typekindmap[oleauto.TKIND_INTERFACE] = 'Interface'
typekindmap[oleauto.TKIND_DISPATCH] = 'Dispatch'
typekindmap[oleauto.TKIND_COCLASS] = 'CoClass'
typekindmap[oleauto.TKIND_ALIAS] = 'Alias'
typekindmap[oleauto.TKIND_UNION] = 'Union'

class TypeBrowseDialog(dyndlg.DialogIndirect):
	"Browse a type library"

	IDC_TYPELIST = 1000
	IDC_MEMBERLIST = 1001
	IDC_PARAMLIST = 1002
	IDC_HELPSTRING = 1003
	IDC_HELPCONTEXT = 1004
	IDC_TYPEKIND = 1005
	IDC_GUID = 1006
	IDC_VERSION = 1007

	def __init__(self, typefile):
		dyndlg.DialogIndirect.__init__(self, self.GetTemplate())
		self.tlb = oleauto.LoadTypeLib(typefile)
		self.dlg.HookCommand(self.CmdTypeListbox, self.IDC_TYPELIST)
		self.dlg.HookCommand(self.CmdMemberListbox, self.IDC_MEMBERLIST)
		self.AddDDX(self.IDC_HELPSTRING, "helpstring")
		self.AddDDX(self.IDC_HELPCONTEXT, "helpcontext")
		self.AddDDX(self.IDC_TYPEKIND, "typekind")
		self.AddDDX(self.IDC_GUID, "guid")
		self.AddDDX(self.IDC_VERSION, "version")
		self['version'] = '0.00'

	def OnInitDialog(self, handler, msg):
		self.typelb = self.GetControl(self.IDC_TYPELIST)
		self.memberlb = self.GetControl(self.IDC_MEMBERLIST)
		self.paramlb = self.GetControl(self.IDC_PARAMLIST)
		n = self.tlb.GetTypeInfoCount()
		for i in range(n):
			self.typelb.AddString(self.tlb.GetDocumentation(i)[0])

	def CmdTypeListbox(self, handler, id, code):
		if code == win32con.LBN_SELCHANGE:
			pos = self.typelb.GetCurSel()
			if pos >= 0:
				self.memberlb.ResetContent()
				self.typeinfo = self.tlb.GetTypeInfo(pos)
				self.attr = self.typeinfo.GetTypeAttr()
				for i in range(self.attr[7]):
					id = self.typeinfo.GetVarDesc(i)[0]
					self.memberlb.AddString(self.typeinfo.GetNames(id)[0])
				for i in range(self.attr[6]):
					id = self.typeinfo.GetFuncDesc(i)[0]
					self.memberlb.AddString(self.typeinfo.GetNames(id)[0])
				docinfo = self.tlb.GetDocumentation(pos)
				self['guid'] = self.attr[0]
				self['helpstring'] = docinfo[1]
				self['helpcontext'] = str(docinfo[2])
				try:
					self['typekind'] = typekindmap[self.tlb.GetTypeInfoType(pos)]
				except:
					pass
			return 1

	def CmdMemberListbox(self, handler, id, code):
		if code == win32con.LBN_SELCHANGE:
			self.paramlb.ResetContent()
			pos = self.memberlb.GetCurSel()
			if pos >= self.attr[7]:
				pos = pos - self.attr[7]
				id = self.typeinfo.GetFuncDesc(pos)[0]
				names = self.typeinfo.GetNames(id)
				for i in range(len(names)):
					if i > 0:
						self.paramlb.AddString(names[i])
				docinfo = self.typeinfo.GetDocumentation(id)
				self['helpstring'] = docinfo[1]
				self['helpcontext'] = str(docinfo[2])
			elif pos >= 0:
				id = self.typeinfo.GetVarDesc(pos)[0]
				self['helpstring'] = docinfo[1]
				self['helpcontext'] = str(docinfo[2])
			return 1

	def GetTemplate(self):
		"Return the template used to create this dialog"

		w = 272  # Dialog width
		h = 192  # Dialog height
		style = FRAMEDLG_STD | win32con.WS_VISIBLE | win32con.DS_SETFONT | win32con.WS_MINIMIZEBOX
		template = [['Type Library Browser', (0, 0, w, h), style, None, (8, 'Helv')], ]
		template.append([130, "&Type", -1, (10, 10, 62, 9), SS_STD | win32con.SS_LEFT])
		template.append([131, None, self.IDC_TYPELIST, (10, 20, 80, 80), LBS_STD])
		template.append([130, "&Members", -1, (100, 10, 62, 9), SS_STD | win32con.SS_LEFT])
		template.append([131, None, self.IDC_MEMBERLIST, (100, 20, 80, 80), LBS_STD])
		template.append([130, "&Parameters", -1, (190, 10, 62, 9), SS_STD | win32con.SS_LEFT])
		template.append([131, None, self.IDC_PARAMLIST, (190, 20, 75, 80), LBS_STD])
		template.append([130, "", self.IDC_HELPSTRING, (60, 170, 205, 18), SS_STD | win32con.SS_LEFT])
		template.append([130, "", self.IDC_HELPCONTEXT, (60, 155, 140, 7), SS_STD | win32con.SS_LEFTNOWORDWRAP])
		template.append([130, "Help String:", -1, (10, 170, 45, 8), SS_STD | win32con.SS_LEFT])
		template.append([130, "Help Context:", -1, (10, 155, 45, 8), SS_STD | win32con.SS_LEFT])
		template.append([130, "Type Kind:", -1, (10, 110, 45, 8), SS_STD | win32con.SS_LEFT])
		template.append([130, "", self.IDC_TYPEKIND, (60, 110, 140, 8), SS_STD | win32con.SS_LEFTNOWORDWRAP])
		template.append([130, "GUID:", -1, (10, 140, 45, 8), SS_STD | win32con.SS_LEFT])
		template.append([130, "", self.IDC_GUID, (60, 140, 160, 8), SS_STD | win32con.SS_LEFTNOWORDWRAP])
		template.append([130, "Version:", -1, (10, 125, 45, 8), SS_STD | win32con.SS_LEFT])
		template.append([130, "", self.IDC_VERSION, (60, 125, 140, 8), SS_STD | win32con.SS_LEFTNOWORDWRAP])

		return template

openFlags = win32con.OFN_OVERWRITEPROMPT | win32con.OFN_FILEMUSTEXIST
fspec = "Type Libraries (*.tlb, *.olb)|*.tlb;*.olb|All Files (*.*)|*.*||"
dlg = win32ui.CreateFileDialog(1, None, None, openFlags, fspec)
if dlg.DoModal() == win32con.IDOK:
	TypeBrowseDialog(dlg.GetPathName()).DoModal()
