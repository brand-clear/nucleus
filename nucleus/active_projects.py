#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module provides objects that store, manipulate, and display active work 
order data for the ``Nucleus`` application.

"""
import sys
import time
import getpass
import operator
from datetime import datetime
from collections import OrderedDict
from PyQt4 import QtGui, QtCore
from pyqtauto.widgets import ImageButton, Spacer, Dialog, ExceptionMessageBox
from pywinscript.winprint import Printer
from job_io import JobIO
from core import Path, Image
from project_view import ProjectTable, NoteBox
from work_orders import WorkOrderConstants
from context import ContextHandler as handler
from context import ProjectContextMenu
from errors import JobInUseError, JobNotFoundError, MultipleJobError


__author__ = 'Brandon McCleary'


class ActiveProjectsDialog(Dialog):
	"""Active project data wrapped inside a ``Dialog`` object."""
	def __init__(self):
		super(ActiveProjectsDialog, self).__init__('Active Projects')
		self.setMinimumSize(800, 600)
		self._active_projects = ActiveProjects()
		self.layout.addWidget(self._active_projects.view)


class ActiveProjects(object):
	"""
	Presents all CAD Department work orders.

	Parameters
	----------
	users : UserData or None
		Data model. 
		If ``None``, the work orders cannot be modified in this context.

	status : StatusBar
		Application broadcast system.

	Attributes
	----------
	view : ActiveProjectView

	See Also
	--------
	work_orders.Project

	"""
	def __init__(self, users=None, status=None):
		self._users = users
		self._status = status
		self._selected_dwg_nums = None
		self._temp_file = 'C:\\Users\\%s\\Desktop\\AP.txt' % getpass.getuser()
		self._printer = Printer(self._temp_file)
		self._model = ActiveProjectModel()
		self.view = ActiveProjectView()
		self.view.table.set_table(self._model.data)
		self.view.table.itemSelectionChanged.connect(self._on_click_project)
		self.view.search_le.textEdited.connect(self._on_edit_text)
		self.view.refresh_btn.clicked.connect(self._on_click_refresh)
		self.view.print_btn.clicked.connect(self._on_click_print)
		self._set_context()

	def _set_context(self):
		"""Initialize context menu if user is allowed to modify work orders."""
		if self._users is not None:
			self._menu = ProjectContextMenu(
				self.view.table,
				response=self._on_click_context,
				active_projects=True
			)
			self.view.table.customContextMenuRequested.connect(self._show_menu)

	def _show_menu(self):
		"""Display ``ProjectTable`` context menu."""
		self._selected_dwg_nums = self.view.table.selected_dwg_nums
		if len(self._selected_dwg_nums) > 0:
			self._menu.popup(QtGui.QCursor.pos())

	def _on_click_context(self, context):
		"""Process context menu actions."""
		context_action = str(self.view.table.sender().text())

		# Attempt to acquire job ownership
		try:
			job_num = self._selected_job_num(self._selected_dwg_nums)
			job, lock = JobIO.job_and_lock(job_num)
		except (
			MultipleJobError, JobInUseError, JobNotFoundError, IOError, 
			EOFError
		)as error:
			ExceptionMessageBox(error).exec_()
			return
		
		# Modify work order data
		if context_action == 'Delete':
			handler.delete(
				self._selected_dwg_nums,
				job.projects
			)
		elif context_action == 'Add Note':
			handler.note(
				self._selected_dwg_nums,
				job.projects,
				self._users.my_name
			)
		elif context == 'Due Dates':
			handler.due_date(
				self._selected_dwg_nums,
				job.projects,
				context_action
			)

		# Attempt to save changes
		try:
			JobIO.save(job_num, job)
		except IOError as error:
			ExceptionMessageBox(error).exec_()

		# Release ownership and update view
		lock.unlock()
		self._status.show_save_msg(job_num)
		self._on_click_refresh()

	def _selected_job_num(self, dwg_nums):
		"""Extract the job number(s) from a collection of drawing numbers.

		Parameters
		----------
		dwg_nums : list

		Returns
		-------
		str
			The job number associated with the selected drawing numbers.

		Raises
		------
		MultipleJobError
			If multiple job numbers were extracted.

		"""
		job_num = {dwg_num[:6] for dwg_num in dwg_nums}
		if len(job_num) != 1:
			raise MultipleJobError()
		return list(job_num)[0]

	def _on_edit_text(self):
		"""Set ``ProjectTable`` per ``QLineEdit`` text."""
		self.view.table.set_table(self._model.filtered(self.view.text))

	def _on_click_print(self):
		"""Process a request to print ``ProjectTable`` data."""
		selected_dwg_nums = self.view.table.selected_dwg_nums
		if len(selected_dwg_nums) > 0:
			# Print selected ProjectTable rows
			self._print_projects(self._model.selected(selected_dwg_nums))
		else:
			# Print existing ProjectTable rows
			existing_dwg_nums = self.view.table.existing_dwg_nums
			self._print_projects(self._model.selected(existing_dwg_nums))

	def _print_projects(self, data):
		"""Create, print, and delete the temp file which contains project data.

		Parameters
		----------
		data : dict
			``Projects`` ordered by their associated drawing numbers.

		"""
		self._write_data_file(data)
		self._printer.start()
		# Wait for file to be sent to printer, otherwise an attempt to delete
		# the file will conflict with the print. Testing shows a 1 second 
		# delay to be sufficient.
		time.sleep(1)
		JobIO.clear_temp_files([self._temp_file])

	def _write_data_file(self, data):
		"""Write project data to file.

		Parameters
		----------
		data : dict
			``Projects`` ordered by their associated drawing numbers.

		"""
		job_num_list = []
		format = WorkOrderConstants.DATE_FORMAT
		timestamp = datetime.now().strftime(format)
		with open(self._temp_file, 'wb') as f:
			f.write('Drafting Dept. Active Project List %s\n\n' % timestamp)
			for dwg_num in data.keys():
				project = data[dwg_num]
				job_num = dwg_num[:6]

				# Write separator to file
				if job_num not in job_num_list:
					job_num_list.append(job_num)
					f.write('#\n')

				# Write project data to file
				f.write(
					'%s . %s . %s . %s\n' % (
						dwg_num, 
						project.owner, 
						project.due_date, 
						project.status
					)
				)

	def _on_click_project(self):
		"""Display project notes per ``ProjectTable`` selection.
		
		Notes
		-----
		No project notes are displayed if multiple projects are selected.

		"""
		self.view.notes.clear()
		selected_projects = self.view.table.selected_dwg_nums
		if len(selected_projects) == 1:
			project = self._model.data[selected_projects[0]]
			self.view.notes.set_notes(project.notes.data)
		else:
			self.view.notes.clear()

	def _on_click_refresh(self):
		"""Update data model and view."""
		self.view.search_le.clear()
		self._model.refresh()
		self.view.table.set_table(self._model.data)


class ActiveProjectModel(object):
	"""
	Contains all active CAD department work order data.

	See Also
	--------
	work_orders.Project
	job_io.JobIO

	"""
	def __init__(self):
		self._data = None
		self.refresh()

	@property
	def data(self):
		"""dict: ``Projects`` ordered by their associated drawing numbers.

		"""
		return self._data

	def refresh(self):
		"""Update data model."""
		self._data = JobIO.existing_projects()

	def filtered(self, value):
		"""Get a data model subset per a given input.

		Parameters
		----------
		value : str
			Text that is checked against data model drawing numbers.

		Returns
		-------
		OrderedDict
			A data model subset that is ordered by drawing number.

		"""
		filtered = {k:v for (k,v) in self.data.items() if value in k}
		return OrderedDict(sorted(filtered.items(), key=operator.itemgetter(0)))

	def selected(self, dwg_nums):
		"""Get a data model subset per a list of drawing numbers.

		Parameters
		----------
		dwg_nums : list

		Returns
		-------
		OrderedDict
			A data model subset that is ordered by drawing number.

		"""
		selected = {}
		for p in dwg_nums:
			selected[p] = self.data[p]
		return OrderedDict(sorted(selected.items(), key=operator.itemgetter(0)))


class ActiveProjectView(QtGui.QWidget):
	"""
	A graphical interface to all CAD department work order data.

	Attributes
	----------
	search_le : QLineEdit
	refresh_btn : ImageButton
	print_btn : ImageButton
	table : ProjectTable
	notes : NoteBox
	text

	"""
	def __init__(self):
		# Build GUI
		super(ActiveProjectView, self).__init__()
		self._layout = QtGui.QVBoxLayout(self)
		self._header_layout = QtGui.QHBoxLayout()
		self._header_layout.addWidget(QtGui.QLabel('Job Number:'))
		self.search_le = QtGui.QLineEdit()
		self.search_le.setFixedWidth(150)
		self._header_layout.addWidget(self.search_le)
		self._header_layout.addItem(Spacer(20, 0, ypolicy='fixed'))
		self.refresh_btn = ImageButton(
			Image.REFRESH,
			self._header_layout,
			tooltip='Refresh',
			flat=True
		)
		self.print_btn = ImageButton(
			Image.PRINT,
			self._header_layout,
			tooltip='Print',
			flat=True
		)
		self.table = ProjectTable()
		self.notes = NoteBox()
		self._layout.addLayout(self._header_layout)
		self._splitter = QtGui.QSplitter()
		self._splitter.setOrientation(QtCore.Qt.Vertical)
		self._splitter.addWidget(self.table)
		self._splitter.addWidget(self.notes)
		self._layout.addWidget(self._splitter)

	@property
	def text(self):
		"""str: ``QLineEdit`` input."""
		return str(self.search_le.text())


if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	app.setStyle(QtGui.QStyleFactory.create('cleanlooks'))
	view = ActiveProjectsDialog()
	view.exec_()
	sys.exit(app.exec_())