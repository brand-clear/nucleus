#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import shutil
import getpass
import logging
import pandas as pd
from PyQt4 import QtGui, QtCore
from pyqtauto.widgets import (
	Dialog, 
	DialogButtonBox, 
	ExceptionMessageBox, 
	Calendar, 
	ProgressDialog
)
from workcenter import WorkCenterManipulations as wcm
from work_orders import Job
from core import Path
from job_io import JobIO
from errors import (
	ColumnError, 
	EmptyModelError, 
	InvalidDatesError, 
	JobNotFoundError, 
	JobInUseError
)


__author__ = 'Brandon McCleary'


logger = logging.getLogger('debugger')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


class GetWorkCenterSource(QtGui.QFileDialog):
	"""
	Prompt the user to select the work center source file that feeds job
	assignment and statistics.

	"""
	def __init__(self):
		self._source_path = os.path.join(Path.CORE, 'workcenter.xlsx')
		super(GetWorkCenterSource, self).__init__(
			caption='Select Work Center Source File',
			directory='C:\\Users\\%s\\Desktop' % getpass.getuser(),
			filter='Excel Workbook (*.xlsx)'
		)
		if self.exec_():
			self._update_data_source()
			# Check for unassigned jobs after every update.
			self._assign_jobs = AssignJobs(self._source_path)

	def _update_data_source(self):
		"""Replace 'workcenter.xlsx' with the selected file."""
		shutil.copy(
			str(self.selectedFiles()[0]), 
			self._source_path
		)


class AssignmentWork(QtCore.QObject):
	"""
	Automates the creation of new job files.

	Creating a new job file is 'assigning' the ``Job`` to ``Nucleus``. Before 
	this assignment, multiple steps are taken to ensure the ``Job`` does not 
	exist.

	Parameters
	----------
	df : DataFrame
		Data model derived from 'workcenter.xlsx'.
		Each row contains information about a distinct project.

	Attributes
	----------
	df

	DATES : pyqtSignal
		Emitted when invalid 'TWI Due Dates' are found in `df`. The invalid 
		``DataFrame`` indices are sent with the emission.

	EXIT : pyqtSignal
		Emitted when irreconcilable errors are raised. The error is sent with
		the emission.

	STEPS : pyqtSignal
		Emitted when the number of processing steps is known. The step count is
		sent with the emission.

	UPDATE : pyqtSignal
		Emitted after each process step has completed. An informative message is
		sent with the emission.

	FINISHED : pyqtSignal
		Emitted when data processing has completed.

	REQD_COLS : list
		Required columns that must exist in `df`.

	"""

	DATES = QtCore.pyqtSignal(object)
	EXIT = QtCore.pyqtSignal(object)
	STEPS = QtCore.pyqtSignal(object)
	UPDATE = QtCore.pyqtSignal(object)
	FINISHED = QtCore.pyqtSignal()

	REQD_COLS = [
		'Work Center Instructions',
		'Status',
		'TWI Due Date',
		'WC line alias',
		'Budgeted hours'
	]

	def __init__(self, df):
		super(AssignmentWork, self).__init__()
		self.df = df

	def start(self):
		"""Data processing thread."""
		try:
			# Filter out errors and unnecessary data
			wcm.check_reqd_cols(self.df, self.REQD_COLS)
			wcm.drop_keyword_condition(self.df, 'Status', 'Unassigned')
			wcm.drop_extra_cols(self.df, self.REQD_COLS)
			self._drop_active_jobs(self.df)
			wcm.format_date_col(self.df, 'TWI Due Date')

			# Get a dictionary of subsampled DataFrames, one for each unique
			# job number.
			job_dfs = wcm.dict_of_df_subs(
				self.df, 
				'WC line alias', 
				wcm.jobs(self.df)
			)

			# Get number of jobs to assign (processing steps)
			job_numbers = job_dfs.keys()
			self.STEPS.emit(len(job_numbers))

			# Create files for all unassigned jobs
			for job_num in job_numbers:
				self._assign_job(job_num, job_dfs[job_num])
				self.UPDATE.emit('%s created successfully...' % job_num)

		except (
			ColumnError, EmptyModelError, IOError, JobNotFoundError, 
			JobInUseError, EOFError
		) as error:
			logger.debug(type(error).__name__)
			self.EXIT.emit(error)

		except InvalidDatesError as error:
			logger.debug(type(error).__name__)
			self.DATES.emit(error.indices)

		else:
			logger.debug('Process completed successfully')
			self.FINISHED.emit()

	def _drop_active_jobs(self, df):
		"""Remove rows that have been assigned.

		Parameters
		----------
		df : DataFrame

		Raises
		------
		EmptyModelError
			All rows in `df` were removed.

		"""
		assigned = JobIO.active_job_nums()
		assigned_indices = [
			index for index, row in df.iterrows()
			if row['WC line alias'][:6] in assigned
		]
		df.drop(assigned_indices, inplace=True)
		if len(df.index) == 0:
			raise EmptyModelError()

	def _transform_row_into_project(self, row, job):
		"""Convert a ``DataFrame`` row into a ``Project``.

		Parameters
		----------
		row : pd.Series

		job : Job

		"""
		job.add_project(
			row['WC line alias'],
			wcm.format_work_instructions(row),
			'Unassigned',
			row['TWI Due Date']
		)

	def _assign_job(self, job_num, df):
		"""Create and update new job files.

		Parameters
		----------
		job_num : str

		df : DataFrame
			Contains information corresponding to `job_num` only.

		Raises
		------
		IOError
		JobNotFoundError
		JobInUseError
		EOFError

		"""
		JobIO.init_files(job_num, None)
		job, lock = JobIO.job_and_lock(job_num)
		for index, row in df.iterrows():
			self._transform_row_into_project(row, job)	
		JobIO.save(job_num, job)
		lock.unlock()


class DateSelectionDialog(Dialog):
	"""
	Prompts the user to correct invalid 'TWI Due Dates'.

	Parameters
	----------
	df : DataFrame
		Contains data for projects with invalid 'TWI Due Dates'.

	Attributes
	----------
	df	

	"""
	def __init__(self, df):
		self.df = df
		# Setup GUI
		super(DateSelectionDialog, self).__init__('Missing TWI Due Dates')
		self._alias_lw = QtGui.QListWidget()
		self._alias_lw.setMaximumWidth(120)
		self._alias_lw.currentTextChanged.connect(self._on_click_alias_lw)
		self._project_sw = QtGui.QStackedWidget()
		self._details_layout = QtGui.QHBoxLayout()
		self._details_layout.setSpacing(10)
		self._details_layout.addWidget(self._alias_lw)
		self._details_layout.addWidget(self._project_sw)
		self.layout.addWidget(
			QtGui.QLabel('Select a "TWI Due Date" for each alias item below.')
		)
		self.layout.addLayout(self._details_layout)

		# Connect buttons with actions
		self._btns = DialogButtonBox(self.layout, 'okcancel')
		self._btns.accepted.connect(self._on_click_ok)
		self._btns.rejected.connect(self.reject)

		# _stack will contain alias numbers as keys and ProjectWithInvalidDate 
		# objects as values. Use this container to switch view widgets.
		self._stack = {}
		self._set_view()

	def _set_view(self):
		"""Generate and display widget sets."""
		for index, row in self.df.iterrows():
			alias = row['WC line alias']
			self._stack[alias] = ProjectWithInvalidDate(row)
			self._project_sw.addWidget(self._stack[alias])
			self._alias_lw.addItem(alias)

	def _on_click_alias_lw(self, alias):
		"""Update view with each ``QListWidget`` selection.
		
		Parameters
		----------
		alias : str
		
		"""
		self._project_sw.setCurrentWidget(self._stack[str(alias)])

	def _on_click_ok(self):
		"""Save user corrections to DataFrame."""
		date_df = self.df.copy()

		# Retrieve corrected dates and add to DataFrame
		for key in self._stack.keys():
			index = self.df.index[self.df['WC line alias'] == key]
			date_df.at[index, 'TWI Due Date'] = self._stack[key].corrected_date

		# Format corrected dates
		date_df['TWI Due Date'] = pd.to_datetime(
			date_df['TWI Due Date'], 
			format='%m/%d/%Y'
		)
		# Update attribute and close window
		self.df = date_df
		self.accept()


class ProjectWithInvalidDate(QtGui.QWidget):
	"""
	Represents a widget set for projects with invalid 'TWI Due Dates'.

	Parameters
	----------
	row : pd.Series

	Attributes
	----------
	corrected_date : str

	"""
	def __init__(self, row):
		super(ProjectWithInvalidDate, self).__init__()
		self._calendar = Calendar()
		self._wci_tb = QtGui.QTextBrowser()
		self._wci_tb.setPlainText(wcm.format_work_instructions(row))
		self._layout = QtGui.QHBoxLayout(self)
		self._layout.addWidget(self._calendar)
		self._layout.addWidget(self._wci_tb)

	@property
	def corrected_date(self):
		"""str: The selected date."""
		return self._calendar.date


class AssignJobs(object):
	"""
	Creates new application files for valid unassigned jobs.
	
	Parameters
	----------
	xlsx_path : str
		Absolute path to work center spreadsheet.
		Required columns: {
			'Work Center Instructions', 
			'Status', 
			'TWI Due Date',
			'Budgeted hours'
		}

	Attributes
	----------
	df : DataFrame
		Extracted from `xlsx_path`.

	view : ProgressDialog
		Displays progress feedback to user.

	work : AssignmentWork
		Processes job assignment data from `df`.

	thread : QThread
		Supports data processing while the main thread is locked by GUI.

	dialog : DateSelectionDialog
		Prompts user for corrections if invalid project dates are found.

	"""
	def __init__(self, xlsx_path):
		# Verify access to workcenter spreadsheet
		try:
			self.df = pd.read_excel(xlsx_path)
		except IOError as error:
			ExceptionMessageBox(error).exec_()
			return

		# Setup GUI
		self.view = ProgressDialog('Assignment In Progress')
		self.view.ok_btn.clicked.connect(self.view.accept)	
		self.view.update('Reviewing data...')
		self.view.show()

		# Begin processing workcenter data
		self.start_worker_thread(self.df)

	def start_worker_thread(self, df):
		"""Launch secondary processing thread.

		Parameters
		----------
		df : DataFrame

		"""
		# Setup threading env
		self.work = AssignmentWork(df)
		self.thread = QtCore.QThread()
		self.work.moveToThread(self.thread)
		self.thread.started.connect(self.work.start)
		# Connect to worker signals
		self.work.DATES.connect(self.on_emit_dates)
		self.work.EXIT.connect(self.on_emit_exit)
		self.work.STEPS.connect(self.on_emit_steps)
		self.work.UPDATE.connect(self.on_emit_update)
		self.work.FINISHED.connect(self.on_emit_finished)
		# Being work
		self.thread.start()

	def thread_cleanup(self):
		"""Kill secondary worker thread."""
		logger.debug(self.thread_cleanup.__doc__)
		self.thread.quit()
		self.thread.wait()

	def on_emit_exit(self, error):
		"""End assignment process due to a given error and display reasoning to 
		user.

		Parameters
		----------
		error : Exception subclass

		"""
		self.thread_cleanup()
		self.view.close()
		ExceptionMessageBox(error).exec_()

	def on_emit_dates(self, indices):
		"""Prompt user to correct invalid 'TWI Due Date' data.

		If the user specifies new dates, an updated ``DataFrame`` containing 
		the corrected dates is passed to the secondary worker thread for another 
		round of processing.

		Parameters
		----------
		indices : list
			Indices for invalid dates in `df`.

		"""
		self.thread_cleanup()
		# Get DataFrame of invalid 'TWI Due Dates' and
		# prompt user for corrections
		df = wcm.df_sub_from_indices(self.df, indices)
		self.dialog = DateSelectionDialog(df)
		if self.dialog.exec_():

			# Update DataFrame with user selections
			self.df.drop(indices, inplace=True)
			self.df = self.df.append(self.dialog.df)
			# Restart process with updated DataFrame
			self.start_worker_thread(self.df)
			
		else:
			self.view.close()

	def on_emit_steps(self, step_count):
		"""Set the number of increments required to complete the assignment
		process.

		Parameters
		----------
		step_count : int

		"""
		self.view.set_step_count(step_count)

	def on_emit_update(self, msg):
		"""Update view with informative message and progress increment.

		Parameters
		----------
		msg : str

		"""
		self.view.update(msg)

	def on_emit_finished(self):
		"""Notify user of process completion and allow exit."""
		self.thread_cleanup()
		self.view.update('Process has completed.')
		self.view.enable_ok()


if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	wcs = GetWorkCenterSource()
	sys.exit(app.exec_())
	