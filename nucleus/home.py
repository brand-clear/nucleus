#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from PyQt4 import QtGui, QtCore
from pyqtauto import setters
from pyqtauto.widgets import Table, TableItem, ImageButton
from active_projects import ActiveProjects
from context import JobContextMenu
from core import Image
from job_io import JobIO


__author__ = 'Brandon McCleary'


class HomeWidget(QtGui.QToolBox):
	"""
	Represents an interface that is tailored to the active user.

	Parameters
	----------
	context_response : callable
		Parent method that is called when the user selects a ``ScheduleTable`` 
		context menu action.

	status : StatusBar
		Application broadcast system.

	users : UserData
		Data model.

	Attributes
	----------
	schedule : ScheduleWidget

	"""
	def __init__(self, context_response, status, users):
		self._context_response = context_response
		self._status = status
		self._users = users
		# Build GUI
		super(HomeWidget, self).__init__()
		setters.set_uniform_margins(self, 40)
		self._set_interface()

	def _set_interface(self):
		"""Set display per user 'Level'."""
		if self._users.my_level is None:
			# Unregistered users view active projects only.
			self._active_proj = ActiveProjects()
			self.addItem(self._active_proj.view, 'Active Projects')
			return

		self.schedule = ScheduleWidget(self._context_response)
		self.addItem(self.schedule, 'Schedule at a Glance')
		if self._users.my_level == 'Supervisor':
			# For supervisors only
			self._active_proj = ActiveProjects(self._users, self._status)
			self.addItem(self._active_proj.view, 'Active Projects')

		# Set view data
		self.schedule.set_view(self._users.my_jobs_at_a_glance)

	def set_view(self, job_dict):
		"""Set ``ScheduleWidget`` contents.

		Parameters
		----------
		job_dict : dict
			Per job_io.JobIO.jobs_at_a_glance.

		"""
		self.schedule.set_view(job_dict)


class ScheduleWidget(QtGui.QWidget):
	"""
	Represents the scheduling portion of a customized user interface.

	Parameters
	----------
	context_response : callable
		Parent method that is called when the user selects a ``ScheduleTable`` 
		context menu action.

	Attributes
	----------
	selected_job_num

	See Also
	--------
	job_io.JobIO

	"""
	def __init__(self, context_response):
		self._context_response = context_response
		# Build GUI
		super(ScheduleWidget, self).__init__()
		self._layout = QtGui.QVBoxLayout(self)
		self._layout.setSpacing(20)
		self._intro_lb = QtGui.QLabel(
			'You do not currently have work assigned to you. \nWhen you do, ' \
				'all job data that is tied to your name will populate here.'
		)
		self._intro_lb.setWordWrap(True)
		self._intro_lb.setAlignment(QtCore.Qt.AlignCenter)
		self._table = ScheduleTable()
		self._table.customContextMenuRequested.connect(self._show_menu)
		self._layout.addWidget(self._intro_lb)
		self._layout.addWidget(self._table)

	@property
	def selected_job_num(self):
		"""str: The selected 6-digit integer that is associated with a 
		collection of work orders.

		"""
		return self._table.selected_job_num

	def set_view(self, job_dict):
		"""Set widget contents.

		Parameters
		----------
		job_dict : dict
			Per job_io.JobIO.jobs_at_a_glance.

		"""
		if len(job_dict) == 0:
			self._intro_lb.show()
		else:
			self._intro_lb.hide()
		self._table.set_table(job_dict)

	def _show_menu(self):
		"""Display the ``ScheduleTable`` context menu."""
		JobContextMenu(
			self._table, 
			self._table.selected_job_num,
			self._context_response
		)


class ScheduleTable(Table):
	"""
	Represents a ``Table`` that contains information about ``Project`` due dates
	for active ``Jobs``.

	Attributes
	----------
	selected_job_num

	See Also
	--------
	work_orders.Job
	work_orders.Project
	job_io.JobIO

	"""

	HEADERS = [
		'Job',
		'Past Due',
		'Due Today',
		'Due Soon'
	]

	def __init__(self):
		super(ScheduleTable, self).__init__(self.HEADERS)
		self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
		self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)

	@property
	def selected_job_num(self):
		"""str or None: The job number associated with the selected row."""
		indices = self.selectionModel().selectedRows()
		try:
			job = str(
				self.item(
					self.selectionModel().selectedRows()[0].row(), 
					self.HEADERS.index('Job')
				).text()
			)
		except IndexError:
			return
		else:
			return job

	def set_table(self, job_dict):
		"""Set ``Table`` contents.

		Parameters
		----------
		job_dict : dict
			Per job_io.JobIO.jobs_at_a_glance.

		"""
		self.setSortingEnabled(False)
		self.setRowCount(0)
		self.setRowCount(len(job_dict))
		jobs = job_dict.keys()
		for i in range(len(jobs)):
			job_num = jobs[i]
			self._set_row(
				i, 
				job_num, 
				job_dict[job_num]['expired'],
				job_dict[job_num]['today'],
				job_dict[job_num]['approaching']
				)
		self.setSortingEnabled(True)

	def _set_row(self, row, job_num, expired, today, approaching):
		"""Set the ``Table`` row.

		Parameters
		----------
		row : int
			``Table`` row index.
			Each row index corresponds to a different ``Job``.

		job_num : str
			The 6-digit job number.

		expired : int
			The number of expired project due dates.

		today : int
			The number of project due dates due today.

		approaching : int
			The number of project due dates that expire within 2 days.

		"""
		job = TableItem(job_num)
		self.setItem(row, 0, job)
		self._set_cell(1, row, expired)
		self._set_cell(2, row, today)
		self._set_cell(3, row, approaching)

	def _set_cell(self, col, row, date_var):
		"""Set the ``Table`` cell value.

		Parameters
		----------
		col : int
			``Table`` column index.
			Every column index except 0 is related to the ``Job's`` project due 
			dates. See HEADERS for column index reference.

		row : int
			``Table`` row index.
			Each row index corresponds to a different job.

		date_var : int
			The number of project due dates that correspond to `col`. 

		"""
		# Use an ImageButton to distinguish 0 from other values.
		if date_var == 0:
			btn = ImageButton(
				Image.ZERO,
				flat=True
			)
			self.setCellWidget(row, col, btn)
		else:
			self.setItem(row, col, TableItem(str(date_var)))


if __name__ == '__main__':
	pass