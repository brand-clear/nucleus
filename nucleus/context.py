#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import win32com.client as win32
from PyQt4 import QtGui, QtCore
from pyqtauto.widgets import (
	Dialog, 
	Spacer, 
	DialogButtonBox, 
	ExceptionMessageBox, 
	Workspace, 
	ComboBox, 
	Calendar
)
from sulzer.extract import Extract, DestinationError, ProjectsFolderRootError
from core import Image, Path
from errors import (
	DrawingNumberError, 
	ProjectNoteError,
	ProjectStorageError, 
	TemplateError, 
	AliasNumberError,
	MissingPDFError
)
from work_orders import WorkOrderConstants
from job_io import JobIO


__author__ = 'Brandon McCleary'


def update_feedback_label(label, text=None, valid=False):
	"""Change the appearance of a ``QLabel`` that displays input feedback.

	If `valid` is False, `text` is ignored and the `label` text will default 
	to an error message.

	Parameters
	----------
	label : QLabel
		``QLabel`` whose text will display feedback.
	text : None or str, optional
		Feedback value, only needed if `valid` is True.
	valid : {False, True}, optional
		Specifies whether the update is a response to valid input.

	"""
	if valid:
		# Set color to black and show text
		label.setStyleSheet('color : rgb(0,0,0)')
		label.setText(text)
	else:
		# Set color to red and show error 
		label.setStyleSheet('color : rgb(255,0,0)')
		label.setText('***')	


class TemplateFileHandler(object):
	"""
	Provides interface to CAD template manipulations and native Autodesk 
	Inventor functions.
	
	"""
	def __init__(self):
		self._app = win32.Dispatch('Inventor.ApprenticeServer')
	
	def copy_paste_template_set(self, template_name, dst_filepath, dst_filename):
		"""Create copies of an Autodesk Inventor template set.

		A template set is composed of an existing IPT/IDW bundle.
		
		Parameters
		----------
		template_name : str
			Name of template file, excluding extension.

		dst_filepath : str
			Absolute path to destination directory.

		dst_filename : str
			Name of template file copy, excluding extension.

		Returns
		-------
		str
			Absolute path to template copy IDW file.
		
		"""
		dst_sans_ext = os.path.join(dst_filepath, dst_filename)
		for ext in ('.ipt', '.idw'):
			src = os.path.join(Path.TEMPLATES, template_name + ext)
			dst = dst_sans_ext + ext
			shutil.copy(src, dst)
		self._set_template_model_ref(dst_sans_ext)
		return dst_sans_ext + '.idw'
		
	def copy_paste_master(self, template_name, dst_filepath, dst_filename):
		"""Create a copy of a blank template file.

		Parameters
		----------
		template_name : str
			Name of template file, including extension.

		dst_filepath : str
			Absolute path to destination directory.

		dst_filename : str
			Name of template file copy, excluding extension.

		Returns
		-------
		dst : str
			Absolute path to template copy.

		"""
		ext = template_name.split('.')[1]
		src = os.path.join(Path.TEMPLATES, template_name)
		dst = os.path.join(dst_filepath, dst_filename + '.' + ext)
		shutil.copy(src, dst)
		return dst
	
	def _set_template_model_ref(self, filepath):
		"""Replace a drawing template's model reference.

		In this context, the drawing and model will have the same name and 
		path, but different extensions (.idw and .ipt, respectively).

		Parameters
		----------
		filepath : str
			Absolute path to template file, excluding extension.

		"""
		dwg = filepath + '.idw'
		model = filepath + '.ipt'
		dwg_obj = self._app.Open(dwg)
		doc = dwg_obj.ReferencedDocumentDescriptors(1).ReferencedFileDescriptor
		doc.ReplaceReference(model)
		self._save(dwg_obj)

	def _save(self, dwg_obj):
		"""Save an open drawing object.

		Parameters
		----------
		dwg_obj : Open drawing object

		"""
		save_obj = self._app.FileSaveAs
		save_obj.AddFileToSave(dwg_obj, dwg_obj.FullFileName)
		save_obj.ExecuteSave()


class RosterContextMenu(QtGui.QMenu):
	"""
	A context menu that appears when the user right-clicks over a 
	``WeekendRosterTable``.

	Parameters
	----------
	parent : WeekendRosterTable

	Attributes
	----------
	refresh : QAction

	"""
	def __init__(self, parent):
		self._parent = parent
		super(RosterContextMenu, self).__init__(self._parent)
		self.refresh = QtGui.QAction(
			QtGui.QIcon(Image.REFRESH), 
			'Refresh', 
			self
		)
		self.addAction(self.refresh)


class JobContextMenu(QtGui.QMenu):
	"""
	A context menu that appears when the user right-clicks over the a 
	``ScheduleTable``.

	Parameters
	----------
	parent : ScheduleTable
		Widget that shows context menu.

	selection : str or None
		The job number associated with the selected ``ScheduleTable`` row.

	response : callable
		Function that is called when a context action is selected.

	See Also
	--------
	home.ScheduleTable

	"""
	def __init__(self, parent, selection_count, response):
		self._parent = parent
		self._selection_count = selection_count
		self._response = response
		# Build GUI
		super(JobContextMenu, self).__init__(self._parent)
		self._add_action('Refresh', Image.REFRESH)
		if self._selection_count is not None:
			self._add_action('Open', Image.OPEN)
			self._add_action('Complete', Image.COMPLETE)
		# Show context menu
		self.popup(QtGui.QCursor.pos())

	def _add_action(self, name, icon):
		"""Create toplevel action.

		Parameters
		----------
		name : str
			Descriptive action text.

		icon : str
			Absolute path to action icon image.

		"""
		action = QtGui.QAction(QtGui.QIcon(icon), name, self)
		action.triggered.connect(self._response)
		self.addAction(action)


class ProjectContextMenu(QtGui.QMenu):
	"""
	A context menu that appears when the user right-clicks over a 
	``ProjectTable``.

	Parameters
	----------
	parent : ProjectTable
		Widget that shows context menu.

	owners : list or None
		Potential project owners.

	selection_count : int or None
		Number of selected ``ProjectTable`` rows.

	response : callable or None
		Function that is called when a context action is selected.

	active_projects : bool
		Context that dictates the ``QMenu`` actions.

	See Also
	--------
	project_view.ProjectTable

	"""
	def __init__(
		self, 
		parent, 
		owners=None, 
		selection_count=None, 
		response=None, 
		active_projects=False
		):
		self._parent = parent
		self._owners = owners
		self._selection_count = selection_count
		self._response = response
		# Build GUI
		super(ProjectContextMenu, self).__init__(self._parent)
		if not active_projects:
			self.single_job_context()
		else:
			self.active_projects_context()
		self.popup(QtGui.QCursor.pos())

	def single_job_context(self):
		"""Generate the context menu for single job displays."""
		self._add_action('New', Image.NEW_PROJECT)
		if self._selection_count == 1:
			self._add_action('Assign Files', Image.ADD)
			self._add_action('Drawing No.', Image.NUMBER)
		if self._selection_count > 0:
			self._add_action('Copy/Paste', Image.COPY)
			self._add_action('Delete', Image.DELETE)
			self._add_action('Add Note', Image.NOTE)
			self._sub_menu(
				'Alias', 
				Image.ALIAS, 
				self._parent.alias_num_options
			)
			self._sub_menu(
				'Owners', 
				Image.OWNER, 
				self._owners
			)
			self._sub_menu(
				'Due Dates', 
				Image.CALENDAR, 
				self._parent.due_date_options
			)
			self._sub_menu(
				'Status', 
				Image.REFRESH, 
				self._parent.status_options
			)
		if self._selection_count == 0:
			self._add_action('Add Files', Image.ADD)

	def active_projects_context(self):
		"""Generate the context menu for the active projects display."""
		self._add_action('Delete', Image.DELETE)
		self._add_action('Add Note', Image.NOTE)
		self._sub_menu(
			'Due Dates', 
			Image.CALENDAR, 
			self._parent.due_date_options
		)

	def _add_action(self, name, icon):
		"""Create toplevel action.

		Parameters
		----------
		name : str
			Descriptive action text.

		icon : str
			Absolute path to action icon image.

		"""
		action = QtGui.QAction(QtGui.QIcon(icon), name, self)
		action.triggered.connect(lambda: self._response(None))
		self.addAction(action)

	def _sub_menu(self, name, icon, actions):
		"""Create submenu with action options.

		Parameters
		----------
		name : str
			Descriptive submenu name.

		icon : str
			Absolute path to submenu icon image.

		actions : list[str]
			Available action options.

		"""
		menu = self.addMenu(QtGui.QIcon(icon), name)
		for a in actions:
			action = QtGui.QAction(a, self)
			action.triggered.connect(lambda: self._response(name))
			menu.addAction(action)	


class BaseModDialog(Dialog):
	"""
	A common ``Dialog`` layout where one or more project names are listed at 
	the top and a ``DialogButtonBox`` is at the bottom.

	The project name(s) correspond to selected ``ProjectTable`` rows that are
	awaiting some form of modification.

	Parameters
	----------
	projects : list
		Selected project name(s) awaiting modification.

	Attributes
	----------
	ws_layout : QVBoxLayout
		Container for ``Workspace`` subclasses.

	btns : DialogButtonBox
		Default buttons. 

	Notes
	-----
	``BaseModDialog`` should be subclassed by other ``Dialog`` objects that 
	represent interfaces to specific project modifications. The modification 
	``Workspace`` objects should be added to `ws_layout`.
	
	"""
	def __init__(self, projects):
		super(BaseModDialog, self).__init__('Edit Project')
		self._header_lb = QtGui.QLabel('Project(s):')
		self._project_lb = QtGui.QLabel('\n'.join(projects))
		self._header_layout = QtGui.QHBoxLayout()
		self._header_layout.setSpacing(5)
		self._header_layout.addWidget(self._header_lb)
		self._header_layout.addWidget(self._project_lb)
		self._header_layout.setAlignment(self._header_lb, QtCore.Qt.AlignTop)
		self._header_layout.setAlignment(self._project_lb, QtCore.Qt.AlignTop)
		self._header_layout.addItem(Spacer(ypad=10, ypolicy='fixed'))
		self.layout.addLayout(self._header_layout)
		self.ws_layout = QtGui.QVBoxLayout()
		self.layout.addLayout(self.ws_layout)
		self.btns = DialogButtonBox(self.layout, 'okcancel')


class NewAliasNumWorkspace(Workspace):
	"""
	A ``Workspace`` responsible for validating work order alias numbers.

	Parameters
	----------
	parent : QLayout subclass

	job_num : str
		A 6-digit integer that is associated with a collection of work orders.

	Attributes
	----------
	alias_num

	See Also
	--------
	work_orders.Job

	"""
	_LABEL_WIDTH = 100

	def __init__(self, parent, job_num):
		self._parent = parent
		self._job_num = job_num
		self._alias_num = None
		# Build GUI
		super(NewAliasNumWorkspace, self).__init__(
			self._parent, 
			'Alias', 
			1000, 
			'QHBoxLayout', 
			flat=False
		)
		self._alias_lb = QtGui.QLabel('New Alias:    %s.' % self._job_num)
		self._alias_lb.setMinimumWidth(self._LABEL_WIDTH)
		self._expressions = QtCore.QRegExp('[0-9]?[0-9]?[0-9]-[0-9][0-9][0-9]')
		self._validator = QtGui.QRegExpValidator(self._expressions)
		self._alias_le = QtGui.QLineEdit()
		self._alias_le.setValidator(self._validator)
		self._alias_le.textEdited.connect(self._on_edit_text)
		self._feedback_lb = QtGui.QLabel()
		self.layout.addWidget(self._alias_lb)
		self.layout.addWidget(self._alias_le)
		self.layout.addWidget(self._feedback_lb)
		self._parent.addWidget(self)
		# Set initial state as invalid
		update_feedback_label(self._feedback_lb)

	@property
	def alias_num(self):
		"""str or None: A validated work order alias.
		
		An alias number is the unique sequence of characters used to track the 
		hours spent on individual work orders.
		
		"""
		return self._alias_num
	
	def _on_edit_text(self):
		"""Check ``QLineEdit`` input against convention and display feedback.
		
		"""
		text = self._alias_le.text()
		splits = text.split('-')
		if len(splits) == 2 and len(splits[1]) != 0:
			# Alias is valid, set property
			update_feedback_label(self._feedback_lb, 'OK', True)
			self._alias_num = self._job_num + '.' + text
		else:
			update_feedback_label(self._feedback_lb)
			self._alias_num = None


class NewDrawingNumWorkspace(Workspace):
	"""
	A ``Workspace`` responsible for validating new drawing numbers.

	Parameters
	----------
	parent : QLayout subclass

	job_num : str
		A 6-digit integer that is associated with a collection of work orders.

	naming_convention : NamingConvention
		Data model.

	Attributes
	----------
	drawing_num

	See Also
	--------
	appdata.NamingConvention

	"""
	_LABEL_WIDTH = 100

	def __init__(self, parent, job_num, naming_convention):
		self._parent = parent
		self._job_num = job_num
		self._naming_convention = naming_convention
		self._map = {'part': None, 'process': None, 'detail': None}
		# Build GUI
		super(NewDrawingNumWorkspace, self).__init__(
			self._parent, 
			'Drawing No.', 
			1000, 
			'QGridLayout', 
			flat=False
		)
		self.layout.setSpacing(15)
		# Part widgets - Section 1 of drawing number
		self._part_lb = QtGui.QLabel('New Part Name:')
		self._part_lb.setMinimumWidth(self._LABEL_WIDTH)
		self._part_abbr_lb = QtGui.QLabel()
		self._part_cb = ComboBox(
			self._naming_convention.part_names, 
			editable=True
		)
		# Process widgets - Section 2 of drawing number
		self._process_lb = QtGui.QLabel('New Process Name:')
		self._process_lb.setMinimumWidth(self._LABEL_WIDTH)
		self._process_abbr_lb = QtGui.QLabel()
		self._process_cb = ComboBox(
			self._naming_convention.process_names, 
			editable=True
		)
		# Detail widgets - Section 3 of drawing number
		self._detail_lb = QtGui.QLabel('New Detail Name:')
		self._detail_lb.setMinimumWidth(self._LABEL_WIDTH)
		self._detail_abbr_lb = QtGui.QLabel()
		self._detail_cb = ComboBox(
			self._naming_convention.detail_names, 
			editable=True
		)
		# Connect actions to triggers
		self._part_cb.editTextChanged.connect(
			lambda: self._show_convention_feedback('part', self._part_abbr_lb)
		)
		self._process_cb.editTextChanged.connect(
			lambda: self._show_convention_feedback(
				'process', 
				self._process_abbr_lb
			)
		)
		self._detail_cb.editTextChanged.connect(
			lambda: self._show_convention_feedback(
				'detail', 
				self._detail_abbr_lb
			)
		)
		# Add widgets to layout
		self.layout.addWidget(self._part_lb, 0, 0)
		self.layout.addWidget(self._part_cb, 0, 1)
		self.layout.addWidget(self._part_abbr_lb, 0, 2)
		self.layout.addWidget(self._process_lb, 1, 0)
		self.layout.addWidget(self._process_cb, 1, 1)
		self.layout.addWidget(self._process_abbr_lb, 1, 2)
		self.layout.addWidget(self._detail_lb, 2, 0)
		self.layout.addWidget(self._detail_cb, 2, 1)
		self.layout.addWidget(self._detail_abbr_lb, 2, 2)
		self.layout.setColumnStretch(1, 200)
		# Set initial state as invalid
		self.show_existing_dwg_num('','','')

	@property
	def drawing_num(self):
		"""str or None: A valid drawing number per the established 
		``NamingConvention``.

		"""
		for k in self._map.keys():
			if self._map[k] is None:
				return
		dwg_num = '%s-%s-%s-%s' % (
			self._job_num, 
			self._map['part'], 
			self._map['process'], 
			self._map['detail']
		)
		return dwg_num

	def _show_convention_feedback(self, convention_type, label):
		"""Display convention feedback via a ``QLabel``.

		Parameters
		----------
		convention_type : {'part', 'process', 'detail'}

		label : {`_part_abbr_lb`, `_process_abbr_lb`, `_detail_abbr_lb`}
			``QLabel`` whose text will display feedback.

		"""
		# Get text from caller
		text = str(self.sender().currentText())
		try:
			# Assume ComboBox list item
			abbr = self._naming_convention.get_convention(convention_type, text)
			update_feedback_label(label, abbr, True)
			self._map[convention_type] = abbr
			
		except IndexError:
			# If no matching convention is found
			text = text.upper()
			if self._naming_convention.valid_custom_input(convention_type, text):
				update_feedback_label(label, text, True)
				self._map[convention_type] = text
			else:
				# Caller text does not conform to convention, show error
				update_feedback_label(label)
				self._map[convention_type] = None

	def show_existing_dwg_num(self, part, process, detail):
		"""Set ``ComboBox`` widgets to custom values.

		Parameters
		----------
		part : str
			Section 1 of drawing number.

		process : str
			Section 2 of drawing number.

		detail : str
			Section 3 of drawing number.

		"""
		part_le = self._part_cb.lineEdit()
		part_le.setText(part)
		process_le = self._process_cb.lineEdit()
		process_le.setText(process)
		detail_le = self._detail_cb.lineEdit()
		detail_le.setText(detail)


class ProjectStorageWorkspace(Workspace):
	"""
	A ``Workspace`` responsible for validating project file storage locations.

	Parameters
	----------
	parent : QLayout

	toplevel : str
		The toplevel project workspace directory.

	Attributes
	----------
	dir

	See Also
	--------
	work_orders.Job
	menu.ProjectWorkspace

	"""
	def __init__(self, parent, toplevel):
		self._parent = parent
		self._toplevel = toplevel
		self._dir = None
		# Build GUI
		super(ProjectStorageWorkspace, self).__init__(
			self._parent, 
			'Storage', 
			1000, 
			'QGridLayout', 
			flat=False
		)
		self.setMinimumHeight(200)
		self._model = QtGui.QFileSystemModel()
		self._model.setRootPath(self._toplevel)
		self._view = QtGui.QTreeView()
		self._view.setModel(self._model)
		self._view.setRootIndex(self._model.index(self._toplevel))
		self._view.setColumnHidden(1, True)
		self._view.setColumnHidden(3, True)
		self._view.setColumnWidth(0, 200)
		self._view.clicked.connect(self._on_select_dir)
		self.layout.addWidget(self._view)


	@property
	def dir(self):
		"""str or None: A directory that stores CAD project files."""
		return self._dir

	def _on_select_dir(self, index):
		"""Set attribute per ``QTreeView`` selection."""
		self._dir = str(self._model.filePath(index))


class AddFilesWorkspace(Workspace):
	"""
	A ``Workspace`` responsible for presenting CAD templates.

	Parameters
	----------
	parent : QLayout subclass

	templates : Templates
		Data model.

	Attributes
	----------
	launch
	template

	See Also
	--------
	appdata.Templates
	context.TemplateFileHandler

	"""
	def __init__(self, parent, templates):
		self._parent = parent
		self._templates = templates
		self._launch = False
		self._template = None
		self._template_handler = TemplateFileHandler()
		self._map = {
			'Clearance': self._templates.clearance_templates,
			'Interference': self._templates.interference_templates,
			'Other': self._templates.other_templates
		}
		# Build GUI
		super (AddFilesWorkspace, self).__init__(
			self._parent, 
			'Template Files', 
			1000, 
			'QHBoxLayout', 
			flat=False
		)
		self._filter_frame = QtGui.QFrame()
		# self._filter_frame.setFixedWidth(130)
		self._filter_layout = QtGui.QVBoxLayout(self._filter_frame)
		self._clr_cb = QtGui.QCheckBox('Clearance')
		self._int_cb = QtGui.QCheckBox('Interference')
		self._other_cb = QtGui.QCheckBox('Other')
		self._launch_cb = QtGui.QCheckBox('Launch upon close')
		self._launch_cb.stateChanged.connect(self._on_select_launch)
		self._filters = [self._clr_cb, self._int_cb, self._other_cb]
		self._template_lw = QtGui.QListWidget()
		self._template_lw.currentRowChanged.connect(self._on_select_item)
		self._template_lw.itemClicked.connect(self._on_click_item)
		# Set filter states and layout
		for check in self._filters:
			check.stateChanged.connect(self._on_click_checkbox)
			check.setCheckState(True)
			check.checkStateSet()
			check.setTristate(False)
			self._filter_layout.addWidget(check)
		self._filter_layout.addItem(Spacer())
		self._filter_layout.addWidget(self._launch_cb)
		# Set main layout
		self.layout.addWidget(self._filter_frame)
		self.layout.addWidget(self._template_lw)
		self._parent.addWidget(self)

	@property
	def launch(self):
		"""bool : A trigger for opening CAD templates."""
		return self._launch

	@property
	def template(self):
		"""str or None: The selected CAD template."""
		return self._template

	def _on_click_item(self, item):
		"""Set attribute per ``QListWidget`` selection."""
		self._template = str(item.text())

	def _on_click_checkbox(self):
		"""Set ``QListWidget`` items per ``QCheckBox`` selections."""
		self._template_lw.clear()
		options = ['None']
		# Get all selected templates
		for check in self._filters:
			if check.isChecked():
				options += self._map[str(check.text())]
		# Show selected templates
		self._template_lw.addItems(self._templates.template_setlist(options))

	def _on_select_item(self):
		"""Display ``QToolTip`` per ``QListWidget`` selection.
		
		Notes
		-----
		A single mouse click will yield a temporary ``QToolTip``. To retain the
		``QToolTip`` display, the user must use the arrow keys or hold the 
		left-click button.

		"""
		try:
			item = str(self._template_lw.currentItem().text())
			if item != 'None':
				QtGui.QToolTip.showText(
					QtGui.QCursor.pos(),
					self._templates.template_image(item)
				)
			else:
				# Hide existing QToolTips
				QtGui.QToolTip.showText(
					QtGui.QCursor.pos(),
					''
				)
		except AttributeError:
			# Current index was removed
			pass

	def _on_select_launch(self):
		"""Set attribute per ``QCheckBox`` state."""
		if self._launch_cb.isChecked():
			self._launch = True
		else:
			self._launch = False	

	def create_files(self, selected_template, selected_dir, dwg_num):
		"""Copy template file(s) to new directory under a new filename.

		Parameters
		----------
		selected_template : str

		selected_dir : str

		dwg_num : str
			Filename for new CAD file(s).

		"""
		if 'RES Master' not in selected_template:
			added_file = self._template_handler.copy_paste_template_set(
				selected_template, selected_dir, dwg_num
			)
		else:
			added_file = self._template_handler.copy_paste_master(
				selected_template, selected_dir, dwg_num
			)
		if self.launch is True:
			os.startfile(added_file)


class AddNoteWorkspace(Workspace):
	"""
	A ``Workspace`` responsible for storing project notes.

	Parameters
	----------
	parent : QLayout subclass

	Attributes
	----------
	note : str

	"""
	def __init__(self, parent):
		self._parent = parent
		self._note = None
		# Build GUI
		super(AddNoteWorkspace, self).__init__(
			self._parent, 
			'Note', 
			1000, 
			flat=False
		)
		self._note_te = QtGui.QPlainTextEdit()
		self.layout.addWidget(self._note_te)

	@property
	def note(self):
		"""str or None: A validated note defined by user input."""
		return self._validate_text()

	def _validate_text(self):
		"""Verify that ``QPlainTextEdit`` input contains visible characters.

		Returns
		-------
		str or None
			`text` if ``QPlainTextEdit`` input is valid, else ``None``.
		
		"""
		text = str(self._note_te.toPlainText())
		mod = text.replace(' ', '') 
		mod = mod.replace('\n', '')
		if len(mod) == 0:
			return None
		else:
			return text


class NewDueDateWorkspace(Workspace):
	"""
	A ``Workspace`` responsible for defining new project due dates.

	Parameters
	----------
	parents : QLayout subclass

	Attributes
	----------
	date

	"""
	def __init__(self, parent):
		self._parent = parent
		# Build GUI
		super(NewDueDateWorkspace, self).__init__(
			self._parent, 
			'Due Date', 
			1000, 
			flat=False
		)
		self._calendar = Calendar(self.layout)
	
	@property
	def date(self):
		"""str: The selected date."""
		return self._calendar.date


class NewAliasNumDialog(BaseModDialog):
	"""
	A ``Dialog`` which prompts the user for a new work order alias number.

	In this context, an existing project's alias number is subject to change 
	per	the user's input.

	Parameters
	----------
	job_num : int
		A 6-digit integer that is associated with a collection of work orders.

	projects : list
		Selected project name(s) awaiting modification.

	Attributes
	----------
	alias_num

	"""
	def __init__(self, job_num, projects):
		self._job_num = job_num
		self._projects = projects
		# Build GUI
		super(NewAliasNumDialog, self).__init__(self._projects)
		self._alias_ws = NewAliasNumWorkspace(self.ws_layout, self._job_num)
		self._alias_ws.setCheckable(False)
		self.btns.accepted.connect(self._on_click_ok)
		self.btns.rejected.connect(self.close)

	@property
	def alias_num(self):
		"""str or None: A validated work order alias.
		
		An alias number is the unique sequence of characters used to track the 
		hours spent on individual work orders.
		
		"""
		return self._alias_ws.alias_num

	def _on_click_ok(self):
		"""Validate input."""
		if self.alias_num is not None:
			self.accept()
		else:
			ExceptionMessageBox(AliasNumberError()).exec_()


class NewDrawingNumDialog(BaseModDialog):
	"""
	A ``Dialog`` which prompts the user for a new project drawing number.

	In this context, an existing project's drawing number is subject to change
	per the user's input.

	Parameters
	----------
	job_num : str
		A 6-digit integer that is associated with a collection of work orders.

	naming_convention : NamingConvention
		Data model.

	projects : list
		Selected project name(s) awaiting modification.

	Attributes
	----------
	drawing_num

	"""
	def __init__(self, job_num, naming_convention, projects):
		self._job_num = job_num
		self._naming_convention = naming_convention
		self._projects = projects
		# Build GUI
		super(NewDrawingNumDialog, self).__init__(self._projects)
		self._drawing_num_ws = NewDrawingNumWorkspace(
			self.ws_layout, 
			self._job_num, 
			self._naming_convention
		)
		self._drawing_num_ws.setCheckable(False)
		self.btns.accepted.connect(self._on_click_ok)
		self.btns.rejected.connect(self.close)

	@property
	def drawing_num(self):
		"""str or None: A valid drawing number per the established 
		``NamingConvention``.

		"""
		return self._drawing_num_ws.drawing_num

	def _on_click_ok(self):
		"""Validate input."""
		if self.drawing_num is not None:
			self.accept()
		else:
			ExceptionMessageBox(DrawingNumberError()).exec_()


class NewDueDateDialog(BaseModDialog):
	"""
	A ``Dialog`` which prompts the user for a new project due date.

	In this context, an existing project's due date is subject to change per 
	the	user's input.

	Parameters
	----------
	projects : list
		Selected project name(s) awaiting modification.

	Attributes
	----------
	data : str

	"""
	def __init__(self, projects):
		self._projects = projects
		# Build GUI
		super(NewDueDateDialog, self).__init__(self._projects)
		self._due_date_ws = NewDueDateWorkspace(self.ws_layout)
		self._due_date_ws.setCheckable(False)
		self.btns.accepted.connect(self.accept)
		self.btns.rejected.connect(self.close)

	@property
	def date(self):
		"""str: The selected due date."""
		return self._due_date_ws.date


class AddNoteDialog(BaseModDialog):
	"""
	A ``Dialog`` which prompts the user for a new project note.

	Parameters
	----------
	projects : list
		Selected project name(s) that will receive the new note.

	Attributes
	----------
	note

	"""
	def __init__(self, projects):
		self._projects = projects
		super(AddNoteDialog, self).__init__(self._projects)
		self._note_ws = AddNoteWorkspace(self.ws_layout)
		self.btns.accepted.connect(self._on_click_ok)
		self.btns.rejected.connect(self.close)
		self._note = None

	@property
	def note(self):
		"""str or None: A validated note defined by user input."""
		return self._note_ws.note

	def _on_click_ok(self):
		"""Validate input."""
		if self.note is not None:
			self.accept()
		else:
			ExceptionMessageBox(ProjectNoteError()).exec_()


class AddFilesDialog(BaseModDialog):
	"""
	A ``Dialog`` which creates the CAD files required to fulfill an existing 
	work order.

	This ``Dialog`` will be called in two contexts: 
	1) Create stand-alone template files that do not affect existing projects
	2) Create template files whose drawing number replaces that of an existing 
	project's.

	Parameters
	----------
	job_num : str
		A 6-digit integer that is associated with a collection of work orders.

	templates : Templates
		Data model.

	naming_convention : NamingConvention
		Data model.

	toplevel : str
		The toplevel project workspace directory.

	project : list
		Selected project name that is requesting CAD files.

	"""
	def __init__(self, job_num, templates, naming_convention, toplevel, project):
		self._job_num = job_num
		self._templates = templates
		self._naming_convention = naming_convention
		self._toplevel = toplevel
		self._project = project
		# Build GUI
		super(AddFilesDialog, self).__init__(self._project)
		self._dwg_num_ws = NewDrawingNumWorkspace(
			self.ws_layout, 
			self._job_num, 
			self._naming_convention
		)
		self._project_dir_ws = ProjectStorageWorkspace(
			self.ws_layout,
			self._toplevel
		)
		self._add_files_ws = AddFilesWorkspace(self.ws_layout, self._templates)
		self._dwg_num_ws.setCheckable(False)
		self._project_dir_ws.setCheckable(False)
		self._add_files_ws.setCheckable(False)
		self.btns.accepted.connect(self._on_click_ok)
		self.btns.rejected.connect(self.close)
		# The context is 'Add Files' (#1 as shown above) if _project has a 
		# length of 0.
		if len(self._project) != 0:
			self._set_current_drawing_num()

	@property
	def drawing_num(self):
		"""str or None: A valid drawing number per the established 
		``NamingConvention``.

		"""
		return self._dwg_num_ws.drawing_num

	def _set_current_drawing_num(self):
		"""Set ``ComboBox`` to reflect the active project conventions."""
		dwg_num_split = self._project[0].split('-')
		if len(dwg_num_split) == 4:
			self._dwg_num_ws.show_existing_dwg_num(
				dwg_num_split[1], 
				dwg_num_split[2], 
				dwg_num_split[3]
			)

	def _on_click_ok(self):
		"""Process request to add template files."""
		try:
			# Check for errors
			vals = [
				self.drawing_num, 
				self._project_dir_ws.dir, 
				self._add_files_ws.template
			]
			errors = [
				DrawingNumberError,
				ProjectStorageError,
				TemplateError
			]
			for i in range(len(vals)):
				if vals[i] is None:
					raise errors[i]()

			if self._add_files_ws.template == 'None':
				raise TemplateError()

			# Create template files
			self._add_files_ws.create_files(
				self._add_files_ws.template, 
				self._project_dir_ws.dir, 
				self.drawing_num
			)
			self.accept()

		except (DrawingNumberError, ProjectStorageError, TemplateError) as error:
			ExceptionMessageBox(error).exec_()


class NewProjectDialog(Dialog):
	"""
	A ``Dialog`` which guides the user through creating a new project.

	Parameters
	----------
	job_num : str
		A 6-digit integer that is associated with a collection of work orders.

	naming_convention : NamingConvention
		Data model.

	templates : Templates
		Data model.

	toplevel : str
		The toplevel project workspace directory.

	Attributes
	----------
	alias_num
	drawing_num
	note
	date

	"""
	def __init__(self, job_num, naming_convention, templates, toplevel):
		self._job_num = job_num
		self._naming_convention = naming_convention
		self._templates = templates
		self._toplevel = toplevel
		# Build GUI
		super(NewProjectDialog, self).__init__('New Project')
		self.setMinimumHeight(700)
		self._central_widget = QtGui.QWidget()
		self._central_layout = QtGui.QVBoxLayout(self._central_widget)
		self._scroll_area = QtGui.QScrollArea()
		self._scroll_area.setWidgetResizable(True)
		self._scroll_area.setFrameShape(QtGui.QFrame.NoFrame)
		self._scroll_area.setWidget(self._central_widget)
		self._alias_ws = NewAliasNumWorkspace(
			self._central_layout, 
			self._job_num
		)
		self._dwg_num_ws = NewDrawingNumWorkspace(
			self._central_layout, 
			self._job_num, 
			self._naming_convention
		)
		self._project_dir_ws = ProjectStorageWorkspace(
			self._central_layout, 
			self._toplevel
		)
		self._add_files_ws = AddFilesWorkspace(
			self._central_layout, 
			self._templates
		)
		self._note_ws = AddNoteWorkspace(self._central_layout)
		self._due_date_ws = NewDueDateWorkspace(self._central_layout)
		self.layout.addWidget(self._scroll_area)
		self._btns = DialogButtonBox(self.layout, 'okcancel')
		self._btns.accepted.connect(self._on_click_ok)
		self._btns.rejected.connect(self.close)

	@property
	def alias_num(self):
		"""str or None: A validated work order alias.
		
		An alias number is the unique sequence of characters used to track the 
		hours spent on individual work orders.
		
		"""
		return self._alias_ws.alias_num

	@property
	def drawing_num(self):
		"""str or None: A valid drawing number per the established 
		``NamingConvention``.

		"""
		return self._dwg_num_ws.drawing_num

	@property
	def note(self):
		"""str or None: A validated note defined by user input."""
		return self._note_ws.note

	@property
	def date(self):
		"""str: The selected date."""
		return self._due_date_ws.date

	def _on_click_ok(self):
		"""Process request to add new project.
		
		Notes
		-----
		Only the template files are created here (if applicable), all other 
		processes required to create a new project are completed separately.
		
		"""
		try:
			# Check for errors
			vals = [
				self.alias_num,
				self.drawing_num, 
				self._add_files_ws.template,
				self.note
			]
			errors = [
				AliasNumberError,
				DrawingNumberError,
				TemplateError,
				ProjectNoteError
			]
			for i in range(len(vals)):
				if vals[i] is None:
					raise errors[i]()

			if self._add_files_ws.template == 'None':
				pass

			else:
				if self._project_dir_ws.dir is None:
					raise ProjectStorageError()
				else:
					# Create template files
					self._add_files_ws.create_files(
						self._add_files_ws.template, 
						self._project_dir_ws.dir, 
						self.drawing_num
					)
			self.accept()

		except (
			AliasNumberError, DrawingNumberError, ProjectStorageError, 
			TemplateError, ProjectNoteError
		) as error:
			ExceptionMessageBox(error).exec_()


class ContextHandler:
	"""
	Provides contextual ``Project`` manipulation methods.

	See Also
	--------
	work_orders

	"""

	@staticmethod
	def due_date(selected_dwg_nums, projects, context):
		"""Modify a project's due date attribute.

		Parameters
		----------
		selected_dwg_nums : list
			Drawing numbers associated with the ``Projects`` that are requesting 
			modification.

		projects : dict
			``Projects`` organized by drawing number.

		context : str
			``QAction`` text, the contextual intent.

		"""
		if context != 'New':
			# User chose a suggested date
			new_date = context
		else:
			# User chose to pick a new date
			dialog = NewDueDateDialog(selected_dwg_nums)
			if dialog.exec_():
				new_date = dialog.date
			else:
				return

		# Update project(s)
		for p in selected_dwg_nums:
			projects[p].due_date = new_date

	@staticmethod
	def note(selected_dwg_nums, projects, user):
		"""Modify a project's notes attribute.

		Parameters
		----------
		selected_dwg_nums : list
			Drawing numbers associated with the ``Projects`` that are requesting 
			modification.

		projects : dict
			``Projects`` organized by drawing number.

		user : str
			Name of the note's author.

		"""
		dialog = AddNoteDialog(selected_dwg_nums)
		if dialog.exec_():
			for p in selected_dwg_nums:
				projects[p].notes.add(dialog.note, user)

	@staticmethod
	def delete(selected_dwg_nums, projects):
		"""Delete an existing project.

		Parameters
		----------
		selected_dwg_nums : list
			Drawing numbers associated with the ``Projects`` that are requesting 
			deletion.

		projects : dict
			``Projects`` organized by drawing number.

		"""
		for p in selected_dwg_nums:
			del projects[p]

	@staticmethod
	def status(selected_dwg_nums, projects, status, workspace):
		"""Modify a project's status attribute.

		Parameters
		----------
		selected_dwg_nums : list
			Drawing numbers associated with the ``Projects`` that are requesting 
			modification.

		projects : dict
			``Projects`` organized by drawing number.

		status : str
			The new status.

		workspace : str
			The toplevel project workspace directory.

		Notes
		-----
		When `status` signifies the completion of a work order, an attempt is 
		made to send the corresponding non-controlled drawing PDF to the issued
		prints folder. This PDF should be created through Autodesk Inventor per
		the local iLogic code, otherwise the resulting PDF name may not match 
		the required convention. In this case, this method will not find the PDF
		and the user will be responsible to completing this action.

		"""
		if status == WorkOrderConstants.STATUS_LIST[-1]:
			job_num = selected_dwg_nums[0][:6]
			dwgs_nums = JobIO.drawing_nums_from_list(selected_dwg_nums)
			target_count = len(dwgs_nums)
			actual_count = 0
			moved_dwg_nums = []
			
			# Get the destination for non-controlled drawing PDFs.
			try:
				dst = Extract.issued_prints_folder(job_num)
			except (DestinationError, ProjectsFolderRootError) as error:
				ExceptionMessageBox(error).exec_()
				return

			pdfs = ContextHandler.workspace_pdfs(workspace)

			for pdf in pdfs:
				if actual_count < target_count:
					# Get the filename and drawing number from pdf.
					# The '_' separator is driven by Inventor iLogic code.
					# Non-controlled PDF files must conform to this convention.
					filename = os.path.basename(pdf)
					target_dwg_num = filename.split('_')[0]

					if target_dwg_num in selected_dwg_nums:
						dst_path = os.path.join(dst, filename)
						shutil.move(pdf, dst_path)
						actual_count += 1
						moved_dwg_nums.append(target_dwg_num)

			# Check for PDFs that should exist, but don't.
			missing_pdfs = [i for i in dwgs_nums if i not in moved_dwg_nums]
			if len(missing_pdfs) != 0:
				MissingPDFError.show(missing_pdfs)

		for p in selected_dwg_nums:
			projects[p].status = status

	@staticmethod
	def workspace_pdfs(workspace):
		"""Get the PDF filepaths found within a folder hierarchy.

		Parameters
		----------
		workspace : str
			The toplevel workspace directory.

		Returns
		-------
		file_paths : list
			The absolute paths of PDF files found within the `workspace` 
			hierarchy.

		"""
		file_paths = []
		for root, dirs, files in os.walk(workspace):
			for f in files:
				if os.path.splitext(f)[1] == '.pdf': 
					file_paths.append(os.path.join(root, f)) 
		return file_paths

	@staticmethod
	def owner(selected_dwg_nums, projects, owner):
		"""Modify a project's owner attribute.

		Parameters
		----------
		selected_dwg_nums : list
			Drawing numbers associated with the ``Projects`` that are requesting 
			modification.

		projects : dict
			``Projects`` organized by drawing number.

		status : str
			The new owner.

		"""
		for p in selected_dwg_nums:
			projects[p].owner = owner

	@staticmethod
	def alias_num(selected_dwg_nums, projects, context):
		"""Modify a project's alias number attribute.

		Parameters
		----------
		selected_dwg_nums : list
			Drawing numbers associated with the ``Projects`` that are requesting 
			modification.

		projects : dict
			``Projects`` organized by drawing number.

		context : str
			``QAction`` text, the contextual intent.

		"""
		if context != 'New':
			# User chose a suggested alias
			new_alias = context
			# for p in selected_dwg_nums:
			# 	projects[p].alias_num = context
		else:
			# User chose to define a new alias
			job_num = selected_dwg_nums[0][:6]
			dialog = NewAliasNumDialog(job_num, selected_dwg_nums)
			if dialog.exec_():
				new_alias = dialog.alias_num
			else:
				return

		# Update project(s)
		for p in selected_dwg_nums:
			projects[p].alias_num = new_alias

	@staticmethod
	def drawing_num(selected_dwg_num, projects, naming_convention):
		"""Modify a project's drawing number reference.

		Parameters
		----------
		selected_dwg_num : list
			Drawing numbers associated with the ``Projects`` that are requesting 
			modification.

		projects : dict
			``Projects`` organized by drawing number.

		naming_convention : NamingConvention
			The drawing number standards library.

		"""
		job_num = selected_dwg_num[0][:6]
		dialog = NewDrawingNumDialog(
			job_num,
			naming_convention,
			selected_dwg_num
		)
		if dialog.exec_():
			ContextHandler._update_drawing_num(
				projects, 
				selected_dwg_num[0], 
				dialog.drawing_num
			)

	@staticmethod
	def _update_drawing_num(projects, old, new):
		"""Update a project's drawing number reference.

		Parameters
		----------
		projects : dict
			``Projects`` organized by drawing number.

		old : str
			The existing drawing number.

		new : str
			The new drawing number.

		"""
		projects[new] = projects[old]
		if old != new:
			del projects[old]

	@staticmethod
	def copy_paste(selected_dwg_nums, job):
		"""Create a copy of an existing project.

		Parameters
		----------
		selected_dwg_nums : list
			Drawing numbers associated with the ``Projects`` that are requesting 
			modification.

		job : Job
			A collection of relevant work orders.

		"""
		for p in selected_dwg_nums:
			new_name = p + ' (%d)' % ContextHandler._get_copy_num(p, job.projects)
			job.add_project(
				new_name,
				job.projects[p].notes.data['Work Instructions'],
				job.projects[p].owner,
				job.projects[p].due_date,
				job.projects[p].status
			)
			job.projects[new_name].alias_num = job.projects[p].alias_num

	@staticmethod
	def _get_copy_num(dwg_num, projects):
		"""Get the copy number for a duplicate project.

		Parameters
		----------
		dwg_num : str
			A reference to an existing ``Project``.

		projects : dict
			``Projects`` organized by drawing number.

		Returns
		-------
		copy_num : int
			The number of existing `dwg_num` copies, plus 1.

		"""
		copy_num = 2
		while True:
			new_dwg_num = dwg_num + ' (%d)' % copy_num
			if ContextHandler._project_exists(new_dwg_num, projects):
				copy_num += 1
			else:
				return copy_num

	@staticmethod
	def _project_exists(dwg_num, projects):
		"""Check a group of projects for an existing drawing number.

		Parameters
		----------
		dwg_num : str
			Possible ``Project`` reference.

		projects : dict
			``Projects`` organized by drawing number.
		
		Returns
		-------
		True
			If `dwg_num` is an existing project.

		"""
		for p in projects.keys():
			if p == dwg_num:
				return True

	@staticmethod
	def assign_files(selected_dwg_num, job, templates, naming_convention, owner):
		"""Create template files for a project and rename the drawing number, 
		owner, and status.

		Parameters
		----------
		selected_dwg_nums : list
			Drawing numbers associated with the ``Projects`` that are requesting 
			modification.

		job : Job
			A collection of relevant work orders.

		templates : Templates
			The drawing template library.

		naming_convention : NamingConvention
			The drawing number standards library.

		owner : str
			Name of the party responsible for the project.

		"""
		dialog = AddFilesDialog(
			job.job_num,
			templates,
			naming_convention,
			job.workspace,
			selected_dwg_num
		)
		if dialog.exec_():
			ContextHandler.status(
				selected_dwg_num, 
				job.projects, 
				WorkOrderConstants.STATUS_LIST[1],
				job.workspace
			)
			ContextHandler.owner(selected_dwg_num, job.projects, owner)
			ContextHandler._update_drawing_num(
				job.projects, 
				selected_dwg_num[0], 
				dialog.drawing_num
			)

	@staticmethod
	def add_files(selected_dwg_num, job, templates, naming_convention):
		"""Create template files that are not bound to an existing project.

		Parameters
		----------
		selected_dwg_nums : list
			Drawing numbers associated with the ``Projects`` that are requesting 
			modification.

		job : Job
			A collection of relevant work orders.

		templates : Templates
			The drawing template library.

		naming_convention : NamingConvention
			The drawing number standards library.

		"""
		dialog = AddFilesDialog(
			job.job_num,
			templates,
			naming_convention,
			job.workspace,
			selected_dwg_num
		)
		dialog.exec_()

	@staticmethod
	def new_project(job, templates, naming_convention, owner):
		"""Create a new project.

		Parameters
		----------
		job : Job
			A collection of relevant work orders.

		templates : Templates
			The drawing template library.

		naming_convention : NamingConvention
			The drawing number standards library.
			
		owner : str
			Name of the party responsible for the project.

		"""
		dialog = NewProjectDialog(
			job.job_num,
			naming_convention,
			templates,
			job.workspace
		)
		if dialog.exec_():
			job.add_project(
				dialog.alias_num,
				dialog.note,
				owner,
				dialog.date,
				WorkOrderConstants.STATUS_LIST[1]
			)
			ContextHandler._update_drawing_num(
				job.projects, 
				dialog.alias_num, 
				dialog.drawing_num
			)


if __name__ == '__main__':
	print ContextHandler.find_workspace_pdfs('C:\\Vault WorkSpace\\Draft\\OEM\\test\\132068')