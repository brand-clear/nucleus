#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import time
import getpass
from os import startfile
import cPickle as pickle
from PyQt4 import QtGui, QtCore
from pyqtauto import setters
from pyqtauto.widgets import ExceptionMessageBox, StatusBar, OrphanMessageBox
from gatekeeper.gatekeeper import GateKeeper
from docks import WeekendSignUp, PartLocator, WeekendRoster
from job_folder import JobFolder
from work_orders import Job
from core import Path, Image
from appdata import AppData
from desk import Desk
from job_io import JobIO
from menu import MenuView, NewJobRequest, CompleteJobRequest, AboutDialog
from admin import GetWorkCenterSource
from active_projects import ActiveProjectsDialog
from errors import (
	WorkspaceError, 
	JobNumberError, 
	ExistingJobError, 
	UnknownError, 
	JobNotFoundError, 
	JobInUseError,
	StartUpError, 
	PasswordError
)


__author__ = 'Brandon McCleary'


class EnterNucleusApp(QtGui.QSplashScreen):
	"""
	Represents the entry point to the ``Nucleus`` application.

	A ``QSplashScreen`` is displayed while ``Nucleus`` data is fetched. If the 
	data load is successful, the user is directed to ``Nucleus``. If 
	unsuccessful, the user is notified of the error and the program will close.

	"""
	def __init__(self):
		# Build GUI
		self.app = QtGui.QApplication(sys.argv)
		self.app.setWindowIcon(QtGui.QIcon(QtGui.QPixmap(Image.LOGO)))
		self.app.setStyle(QtGui.QStyleFactory.create('cleanlooks'))
		super(EnterNucleusApp, self).__init__(
			QtGui.QPixmap(Image.LOGO), 
			QtCore.Qt.WindowStaysOnTopHint
		)
		self.show()
		self.showMessage('Loading...', QtCore.Qt.AlignCenter, QtCore.Qt.white)
		self.start_app()

	def start_app(self):
		"""Call the appropriate user interface."""
		try:
			# time.sleep(2)  # Throttle process for visual effect.
			self.app_data = self._load_data()
		except StartUpError as error:
			self.close()
			ExceptionMessageBox(error).exec_()
		else:
			self.finish(Nucleus(self.app_data))
			sys.exit(self.app.exec_())

	def _load_data(self, attempts=3):
		"""Retrieve core data for Nucleus app.

		Parameters
		----------
		attempts : int, optional
			The number of data-loading attempts before raising an error. Each 
			attempt is called 1 second apart.

		Returns
		-------
		data : AppData

		Raises
		------
		StartUpError
			If data could not be loaded.

		"""
		for i in range(attempts):
			try:
				data = AppData(Path.DATA_XLSX)
			except (IOError, EOFError, OSError):
				if (i+1) == attempts:
					raise StartUpError()
				time.sleep(1)
			else:
				return data


class Nucleus(QtGui.QMainWindow):
	"""
	Nucleus is a Sulzer software application that aims to track, schedule, and 
	optimize the work performed by the CAD Department at Sulzer RES La Porte.

	Parameters
	----------
	app_data : AppData
		Core application data source.

	Attributes
	----------
	status : StatusBar
	menu_view : MenuView
	part_locator : PartLocator
	weekend_signup : WeekendSignUp
	weekend_roster : WeekendRoster
	desk : Desk

	"""
	def __init__(self, app_data):
		self.app_data = app_data
		# Build GUI
		super(Nucleus, self).__init__()
		self.resize(1100,600)
		setters.set_uniform_margins(self, 15)
		self.setWindowTitle('Nucleus 2020')
		self.status = StatusBar(self)
		self.set_menu()
		self.set_docks()
		self.desk = Desk(self.app_data, self.status, self.on_click_context)
		self.setCentralWidget(self.desk)
		self.show()

	def set_docks(self):
		"""Display ``QDockWidgets`` per user registration level."""
		self.part_locator = PartLocator(Path.PART_LOC_XLSX)
		self.addDockWidget(
			QtCore.Qt.RightDockWidgetArea, 
			self.part_locator.view
		)

		if self.app_data.users.my_level is None:
			# User is not registered
			return

		self.weekend_roster = WeekendRoster(self.app_data.users)
		self.addDockWidget(
			QtCore.Qt.RightDockWidgetArea, 
			self.weekend_roster.view
		)
		self.weekend_signup = WeekendSignUp(self.app_data.users.my_folder)
		self.addDockWidget(
			QtCore.Qt.RightDockWidgetArea, 
			self.weekend_signup.view
		)

		if self.app_data.users.my_level == 'Technician':
			self.weekend_roster.view.hide()

	def set_menu(self):
		"""Set ``MenuBar`` state per user registration level."""
		self.menu_view = MenuView(self)
		if self.app_data.users.my_level is None:
			# Disable certain features for non-registered members.
			self.menu_view.file_menu.setEnabled(False)
			self.menu_view.view_menu.setEnabled(False)
			self.menu_view.admin_menu.setEnabled(False)
		else:
			self.menu_view.new.triggered.connect(self.on_click_new)
			self.menu_view.open.triggered.connect(self.on_click_open)
			self.menu_view.save.triggered.connect(self.on_click_save)
			self.menu_view.complete.triggered.connect(self.on_click_complete)
			self.menu_view.active_projects.triggered.connect(
				lambda: ActiveProjectsDialog().exec_()
			)
			self.menu_view.upload_data.triggered.connect(self.on_click_upload)
		
		# Visible to all users.
		self.menu_view.about.triggered.connect(lambda: AboutDialog().exec_())
		self.menu_view.version.triggered.connect(
			lambda: startfile(Path.VERSION_DOC)
		)

	def on_click_new(self):
		"""Process a request to create a new ``Job``."""
		job_num, ok = QtGui.QInputDialog.getInt(self, 'New', 'Job Number:')
		if ok:
			job_num = str(job_num)
			request = NewJobRequest(job_num, self.app_data.users.log)
			try:
				# An approved request initializes job files and directories.
				if request.approved():
					self.load_job(job_num)
			except (
				JobNumberError, ExistingJobError, OSError, 
				WorkspaceError, IOError, UnknownError
			) as error:
				ExceptionMessageBox(error).exec_()

	def on_click_open(self):
		"""Prompt user for job number input."""
		job_num, ok = QtGui.QInputDialog.getInt(self, 'Open', 'Job Number:')
		if ok:
			self.process_open_job_request(str(job_num))

	def process_open_job_request(self, job_num):
		"""Process a request to open an existing ``Job``.

		Parameters
		----------
		job_num : str
			The 6-digit job number.

		"""
		try:
			if len(job_num) != 6:
				raise JobNumberError()
			self.load_job(job_num)
		except (
			JobNumberError, OSError, JobNotFoundError, 
			JobInUseError, IOError, EOFError
		) as error:
			ExceptionMessageBox(error).exec_()

	def on_click_save(self):
		"""Process a request to save ``Job`` data."""
		self.desk.save()

	def on_click_complete(self):
		"""Initiate a request to complete the active ``JobFolder``."""
		try:
			job_num = self.desk.active_folder
			job_folder = self.desk.job_folder(job_num)
			job, lock = job_folder.job_and_lock()
			if self.process_complete_job_request(job_num, job, lock):
				self.desk.close_folder(job_num)

		except KeyError:
			# If 'Home' interface is active.
			self.status.showMessage(
				'Cannot complete a job in this context.',
				2000
			)

	def process_complete_job_request(self, job_num, job=None, lock=None):
		"""Process a request to remove job files from ``Nucleus``.
		
		Parameters
		----------
		job_num : str
			The 6-digit job number.

		job : Job or None
			A collection of work orders requesting completion.

		lock : GateKeeper or None
			Controls read and write access to `job` applicaton files.

		Returns
		-------
		True
			If `job` files were removed from ``Nucleus``.
		
		"""
		request = CompleteJobRequest(
			job_num, 
			self.app_data.users.supervisor_email_addresses,
			job,
			lock
		)
		try:
			if not request.approved():
				return
		except (JobInUseError, IOError, EOFError) as error:
			ExceptionMessageBox(error).exec_()
		else:
			self.app_data.users.log(
				'%s completed, due by %s' % (job_num, JobIO.job_due_date(job))
			)
			self.app_data.users.log(
				'%s drawing count: %d' % (job_num, request.dwg_count)
			)
			self.status.showMessage('%s closed successfully.' % job_num)
			self.desk.refresh_home()
			return True

	def is_admin(self):
		"""Confirm that a user has admin credentials for a restricted action.

		Returns
		-------
		True
			If user has admin credentials.

		Raises
		------
		PasswordError
			If user enters incorrect password.

		"""
		password, ok = QtGui.QInputDialog.getText(
			self, 
			'Admin', 
			'Password:', 
			mode=QtGui.QLineEdit.Password
		)
		if ok:
			if password == 'respect':
				return True
			raise PasswordError()

	def on_click_upload(self):
		"""Process request to load work center data."""
		try:
			if self.is_admin():
				self._intent = GetWorkCenterSource()
		except PasswordError as error:
			ExceptionMessageBox(error).exec_()
			self.on_click_upload()
		else:
			self.desk.refresh_home()

	def load_job(self, job_num):
		"""Send a ``Job`` to `desk` and open for viewing.

		Parameters
		----------
		job_num : str
			The 6-digit job number.

		Raises
		------
		JobNotFoundError
		JobInUseError
		IOError
		EOFError

		"""
		job, lock = JobIO.job_and_lock(job_num)
		self.desk.open_job_folder(job, lock)

	def closeEvent(self, event):
		"""Verify that `desk` does not have open ``JobFolders`` before closing 
		window.

		Parameters
		----------
		event : QEvent
			Window close.

		"""
		if self.desk.cleared:
			self.app_data.users.log('logged out')
			event.accept()
		else:
			OrphanMessageBox(
				'Info', 
				['Open jobs must be closed before exiting.'], 
				'information'
			).exec_()
			event.ignore()

	def on_click_context(self):
		"""Process a context menu selection."""
		action = str(self.desk.home.schedule.sender().text())
		if action == 'Open':
			self.process_open_job_request(
				self.desk.home.schedule.selected_job_num
			)

		elif action == 'Complete':
			job_num = self.desk.home.schedule.selected_job_num
			if self.desk.folder_index(job_num):
				# folder_index is used to determine if the associated
				# JobFolder is open. If the user already has this JobFolder 
				# open, route this process to the file menu action.
				self.desk.activate_folder(job_num)
				self.on_click_complete()
			else:
				self.process_complete_job_request(job_num)

		elif action == 'Refresh':
			self.desk.refresh_home()


if __name__ == "__main__":

	EnterNucleusApp()
