#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time
from PyQt4 import QtGui, QtCore
from pyqtauto.widgets import (
	ImageButton, 
	Workspace, 
	Dialog, 
	DialogButtonBox, 
	ExceptionMessageBox
)
from pywinscript.msoffice import send_email
from pywinscript.winprint import Printer
from sulzer.extract import (
	Extract, 
	ProjectsFolderRootError, 
	DestinationError, 
	PicturesFolderRootError
)
from project_view import ProjectTable, NoteBox
from core import Image, Path
from context import ProjectContextMenu
from context import ContextHandler as handler
from job_io import JobIO
from errors import SecurityError
from work_orders import WorkOrderConstants


__author__ = 'Brandon McCleary'


class JobFolder(object):
	"""

	Parameters
	----------
	job : Job
		A collection of work orders.

	lock : GateKeeper
		Controls read and write access to `job` applicaton files.

	app_data : AppData
		Core application data model.

	Attributes
	----------
	view : JobFolderView

	"""
	def __init__(self, job, lock, app_data):
		self._job = job
		self._job_num = self._job.job_num
		self._projects = self._job.projects
		self._lock = lock
		self._naming_convention = app_data.naming_convention
		self._templates = app_data.templates
		self._users = app_data.users
		self._agreements = app_data.agreements
		self._selected_dwg_nums = None
		# Build GUI
		self.view = JobFolderView()
		self._shortcuts = ShortcutActions(
			self._job_num, 
			self._job.workspace, 
			self._users
		)
		# Connect view with actions
		self.view.p_folder_btn.clicked.connect(
			lambda: self._shortcuts.open_path('projects folder')
		)
		self.view.p_folder_btn.setToolTip(
			self._shortcuts.paths['projects folder']
		)
		self.view.rev_engr_btn.clicked.connect(
			lambda: self._shortcuts.open_path('reverse engineering')
		)
		self.view.rev_engr_btn.setToolTip(
			self._shortcuts.paths['reverse engineering']
		)
		self.view.vault_btn.clicked.connect(
			lambda: self._shortcuts.open_path('vault workspace')
		)
		self.view.vault_btn.setToolTip(
			self._shortcuts.paths['vault workspace']
		)
		self.view.photo_btn.clicked.connect(
			lambda: self._shortcuts.open_path('photos')
		)
		self.view.photo_btn.setToolTip(self._shortcuts.paths['photos'])
		self.view.probes_btn.clicked.connect(self._shortcuts.send_probe_email)
		self.view.table.customContextMenuRequested.connect(self._context_menu)
		self.view.table.itemSelectionChanged.connect(self._on_click_project)
		# Set view
		self._update_projects()

	def _update_projects(self):
		"""Set ``ProjectTable`` with current project data."""
		self.view.table.set_table(self._projects)

	def _on_click_project(self):
		"""Display project notes per ``ProjectTable`` selection.
		
		Notes
		-----
		No project notes are displayed if multiple projects are selected.

		"""
		self.view.notes.clear()
		self._selected_dwg_nums = self.view.table.selected_dwg_nums
		if len(self._selected_dwg_nums) == 1:
			project = self._projects[self._selected_dwg_nums[0]]
			self.view.notes.set_notes(project.notes.data)
		else:
			self.view.notes.clear()

	def _context_menu(self):
		"""Show a context menu when the ``ProjectTable`` is right-clicked."""
		self._selected_dwg_nums = self.view.table.selected_dwg_nums
		ProjectContextMenu(
			self.view.table, 
			self._users.technician_names, 
			len(self._selected_dwg_nums), 
			self._on_click_context_action
		)

	def _on_click_context_action(self, context):
		"""Process a context menu selection.

		Parameters
		----------
		context : str or None
			``None`` if a toplevel action was clicked, otherwise the name of the
			submenu that contained the selected action.

		"""
		# Selected action text
		context_action = str(self.view.table.sender().text())
		if context == 'Alias':
			handler.alias_num(
				self._selected_dwg_nums,
				self._projects, 
				context_action
			)
		elif context == 'Owners':
			handler.owner(
				self._selected_dwg_nums,
				self._projects,
				context_action
			)
		elif context == 'Due Dates':
			handler.due_date(
				self._selected_dwg_nums, 
				self._projects,
				context_action
			)
		elif context == 'Status':
			handler.status(
				self._selected_dwg_nums,
				self._projects,
				context_action,
				self._job.workspace
			)
		elif context_action == 'New':
			handler.new_project(
				self._job,
				self._templates,
				self._naming_convention,
				self._users.my_name
			)
		elif context_action == 'Assign Files':
			handler.assign_files(
				self._selected_dwg_nums,
				self._job,
				self._templates,
				self._naming_convention,
				self._users.my_name
			)
		elif context_action == 'Add Files':
			handler.add_files(
				self._selected_dwg_nums,
				self._job,
				self._templates,
				self._naming_convention
			)
		elif context_action == 'Drawing No.':
			handler.drawing_num(
				self._selected_dwg_nums,
				self._projects,
				self._naming_convention
			)
		elif context_action == 'Copy/Paste':
			handler.copy_paste(
				self._selected_dwg_nums,
				self._job
			)
		elif context_action == 'Delete':
			handler.delete(
				self._selected_dwg_nums,
				self._projects
			)
		elif context_action == 'Add Note':
			handler.note(
				self._selected_dwg_nums, 
				self._projects, 
				self._users.my_name
			)
		self._update_projects()

	def save(self, on_close=False):
		"""Save ``Job`` data to file.

		Parameters
		----------
		on_close : bool, optional
			Defines whether this ``JobFolder`` will close after save. If so,
			the job lock will be released.

		Returns
		-------
		True
			If ``Job`` data was saved to file.

		Raises
		------
		SecurityError
			If user does not have rights to save ``Job``.
		IOError
			If no such file or directory.

		"""
		if self._lock.lock_is_acquired:
			if JobIO.save(self._job_num, self._job):
				if on_close:
					self._lock.unlock()
				return True
		else:
			raise SecurityError()

	def job_and_lock(self):
		return self._job, self._lock


class JobFolderView(QtGui.QWidget):
	"""
	Represents the graphical interface to a ``JobFolder``.

	Attributes
	----------
	vault_btn : ImageButton
	p_folder_btn : ImageButton
	rev_engr_btn : ImageButton
	photo_btn : ImageButton
	probes_btn : ImageButton
	agree_btn : ImageButton
	table : ProjectTable
	notes : NoteBox

	"""

	BUTTON_SIZE = 45

	def __init__(self):
		super(JobFolderView, self).__init__()
		self._layout = QtGui.QVBoxLayout(self)

		# Shortcut-based widgets
		self._shortcuts = Workspace(
			self._layout, 
			'Shortcuts', 
			100, 
			'QHBoxLayout'
		)
		self.vault_btn = ImageButton(Image.VAULT, self._shortcuts.layout)
		self.p_folder_btn = ImageButton(Image.P_FOLDER, self._shortcuts.layout)
		self.rev_engr_btn = ImageButton(Image.REV_ENGR, self._shortcuts.layout)
		self.photo_btn = ImageButton(Image.CAMERA, self._shortcuts.layout)
		self.probes_btn = ImageButton(
			Image.EMAIL, 
			self._shortcuts.layout, 
			tooltip='Request Probe Locations'
		)
		self.agree_btn = ImageButton(
			Image.AGREEMENT, 
			self._shortcuts.layout, 
			tooltip='User Agreement'
		)

		# Set ImageButton sizes
		for i in range(self._shortcuts.layout.count()):
			item = self._shortcuts.layout.itemAt(i)
			item.widget().mysquare = self.BUTTON_SIZE

		# Project-based widgets
		self._projects = Workspace(self._layout, 'Projects', 1000)
		self._splitter = QtGui.QSplitter()
		self._splitter.setOrientation(QtCore.Qt.Vertical)
		self.table = ProjectTable()
		self.notes = NoteBox()
		self._splitter.addWidget(self.table)
		self._splitter.addWidget(self.notes)
		self._projects.layout.addWidget(self._splitter)


class ShortcutActions(object):
	"""
	Contains responsive actions for shortcut-based triggers in the 
	``JobFolderView`` class.

	Parameters
	----------
	job_num : str
		A 6 digit integer that represents a collection of work orders.

	workspace : str
		A validated directory that stores project files for `job_num`.

	users : UserData
		Contains application user data.

	Attributes
	----------
	workspace : str
	paths : dict
		A map of directories related to `job_num`.

	"""
	def __init__(self, job_num, workspace, users):
		self._job_num = job_num
		self.workspace = workspace
		self._users = users
		self._set_paths()
		self._to, self._cc, self._subject, self._body = self._probe_email_data()

	def _set_paths(self):
		"""Set functional shortcut paths."""

		# Get functional P_FOLDER path
		try:
			pfolder = Extract.projects_folder(self._job_num)
		except (ProjectsFolderRootError, DestinationError, OSError):
			pfolder = Path.P_FOLDER

		# Get functional REV_ENGR path
		job_rev_engr = os.path.join(Path.REV_ENGR, self._job_num)
		if os.path.exists(job_rev_engr):
			rev_engr = job_rev_engr
		else:
			rev_engr = Path.REV_ENGR

		# Get functional PHOTOS path
		try:
			photos = Extract.pictures_folder(self._job_num)
		except (PicturesFolderRootError, DestinationError, OSError):
			photos = Path.PHOTOS

		# Save reference to paths
		self.paths = {
			'vault workspace': self.workspace,
			'projects folder': pfolder,
			'reverse engineering': rev_engr,
			'photos': photos
		}

	def _probe_email_data(self):
		"""
		Returns
		-------
		list
			Email addresses in 'To' section

		list
			Email addresses in 'Cc' section

		str
			Email subject line

		str
			Email body text

		"""
		subject = '%s Probe Target Request' % self._job_num
		body = ('To all,<br><br>Will you please send the probe locations '
				'for job %s?<br><br>Thank you,<br><br>' % self._job_num)
		to = self._users.probe_email_addresses('To')
		cc = self._users.probe_email_addresses('Cc')
		return to, cc, subject, body

	def send_probe_email(self):
		"""
		Raises
		------
		com_error
			Likely a network issue

		"""
		send_email(self._to, self._cc, self._subject, self._body, True)
		self._users.log('requested %s probe locations' % self._job_num)

	def open_path(self, path):
		"""
		Parameters
		----------
		path : {
			'vault workspace', 'projects folder', 'reverse engineering', 'photos'
			}

		Returns
		-------
		True
			If the operation completed successfully.
		
		Raises
		------
		OSError
			If the system cannot find the file specified.

		"""
		try:
			os.startfile(self.paths[path])
		except OSError:
			# Network connection error
			raise
		else:
			return True


class UserAgreement(object):
	"""Represents a contract by which 'Technician' users should operate.

	Parameters
	----------
	df : DataFrame
		Contains 'Technician' user responsibilities.
		Required columns: {'Agreements'}

	username : str
		Username of the active user.

	name : str
		Given name of the active user.

	Attributes
	----------
	view : UserAgreementView

	"""
	def __init__(self, df, username, name):
		self._username = username
		self._name = name
		self.job_num = None
		self._data = self._get_data(df)
		self.view = UserAgreementView(self._data)
		self.view.ok.accepted.connect(self._on_click_ok)
		self._temp_file = 'C:\\Users\\%s\\Desktop\\UA.txt' % self._username
		self._printer = Printer(self._temp_file)

	def _get_data(self, df):
		"""Returns a ``list`` of user responsibilities."""
		return [row['Agreements'] for index, row in df.iterrows()]

	def _on_click_ok(self):
		"""Print the user agreement and exit."""
		self._write_data_file()
		self._printer.start()
		time.sleep(1)
		JobIO.clear_temp_files([self._temp_file])
		self.view.accept()

	def _write_data_file(self):
		"""Write user agreement to file."""
		with open(self._temp_file, 'wb') as f:
			f.write('Job: %s\n\n\n' % self.job_num)
			f.write(self._data[0] + '\n\n')
			for item in self._data[1:]:
				f.write('\n' + item + '\n\n')
			f.write('\nSigned: %s' % self._name)


class UserAgreementView(Dialog):
	"""Displays 'Technician' user responsibilities.
	
	Parameters
	----------
	agreements : list
		A collection of user responsibilities.

	"""
	def __init__(self, agreements):
		# Build GUI
		super(UserAgreementView, self).__init__('User Agreement')
		self.layout.setSpacing(20)
		for agreement in agreements:
			self.layout.addWidget(QtGui.QLabel(agreement))
		self.ok = DialogButtonBox(self.layout, 'ok')


if __name__ == '__main__':
	pass
