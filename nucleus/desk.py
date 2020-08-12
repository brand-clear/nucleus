#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os.path
from PyQt4 import QtGui
from pyqtauto.widgets import ExceptionMessageBox, Ask
from job_folder import JobFolder, UserAgreement
from menu import ProjectWorkspace
from errors import SecurityError
from core import Image
from home import HomeWidget
from context import JobContextMenu


__author__ = 'Brandon McCleary'


class Desk(QtGui.QTabWidget):
	"""
	Represents a platform upon which ``JobFolder`` objects can be stored, 
	viewed, saved, and closed.
	
	Parameters
	----------
	app_data : AppData
		Application data source.

	status : StatusBar
		Application broadcast system.

	context_response : callable
		Called when the user selects a ``ScheduleTable`` context menu action.

	See Also
	--------
	job_folder.JobFolder
	work_orders.Job
	appdata.AppData
	
	"""
	def __init__(self, app_data, status, context_response):
		self._app_data = app_data
		self._status = status  
		self._context_response = context_response
		self._folders = {} # Will store active JobFolder objects
		self._user_agreement = UserAgreement(
			self._app_data.agreements, 
			self._app_data.users.my_username,
			self._app_data.users.my_name
		)
		# Build GUI
		super(Desk, self).__init__()
		self.setTabsClosable(True)
		self.tabCloseRequested.connect(self._on_click_close)
		self._set_home()

	@property
	def cleared(self):
		"""bool: True if all ``JobFolder`` objects have been closed."""
		return self.count() == 1

	@property
	def active_folder(self):
		"""str: Name of the active folder or interface."""
		return str(self.tabText(self.currentIndex()))

	def _set_home(self):
		"""Display a customized interface for the active user."""
		self.home = HomeWidget(
			self._context_response, 
			self._status, 
			self._app_data.users
		)
		self.addTab(self.home, 'Home')
		self.tabBar().setTabButton(0, QtGui.QTabBar.RightSide, None)

		# Broadcast login
		if self._app_data.users.my_name is not None:
			self._status.show_login_msg(self._app_data.users.my_name)
		else:
			self._status.show_login_msg(self._app_data.users.my_username)	

	def refresh_home(self):
		"""Update the user's home interface."""
		self.home.set_view(self._app_data.users.my_jobs_at_a_glance)

	def _show_agreement(self, job_num):
		"""Display the user agreement."""
		self._app_data.users.log('viewed %s user agreement' % job_num)
		self._user_agreement.job_num = job_num
		self._user_agreement.view.exec_()

	def job_folder(self, job_num):
		"""Returns a ``JobFolder``.

		Parameters
		----------
		job_num : str
			The 6-digit job number that is associated with the ``JobFolder``.
		
		Raises
		------
		KeyError
			If `job_num` is not a valid `_folders` key.
			
		"""
		return self._folders[job_num]

	def folder_index(self, folder_name):
		"""Returns a folder's ``QTabWidget`` index.

		Parameters
		----------
		folder_name : str
			A 6-digit job number or 'Home'.

		"""
		for index in range(self.count()):
			if folder_name == str(self.tabText(index)):
				return index

	def activate_folder(self, folder_name):
		"""Set the active folder.

		Parameters
		----------
		folder_name : str
			A 6-digit job number or 'Home'.

		"""
		self.setCurrentIndex(self.folder_index(folder_name))
 
	def open_job_folder(self, job, lock):
		"""Load and display ``JobFolder`` contents.

		Parameters
		----------
		job : Job
			A collection of work orders.

		lock : GateKeeper
			Controls read and write access to `job` files.

		"""
		if self._has_workspace(job):
			self._app_data.users.log('opened job %s' % job.job_num)
			self._folders[job.job_num] = JobFolder(job, lock, self._app_data)
			self._folders[job.job_num].view.agree_btn.clicked.connect(
				lambda: self._show_agreement(job.job_num)
			)
			self.addTab(self._folders[job.job_num].view, job.job_num)
			self.setCurrentIndex(self.count()-1)
		else:
			lock.unlock()

	def save(self):
		"""Serialize ``Job`` data."""
		folder = self.active_folder
		if folder != 'Home':
			try:
				self._folders[folder].save()
			except (IOError, SecurityError) as error:
				ExceptionMessageBox(error).exec_()
			else:
				self._app_data.users.log('saved job %s' % folder)
				self._status.show_save_msg(folder)
		else:
			self._status.showMessage(
				'Cannot save a job in this context.', 
				2000
			)

	def _has_workspace(self, job):
		"""Enforce a valid ``Job`` workspace.

		Parameters
		----------
		job : Job
			A collection of work orders.

		Returns
		-------
		True
			If `job` contains a valid project workspace path.

		"""
		if job.workspace is None or not os.path.exists(job.workspace):
			# No workspace has been defined (admin auto-add) or the initial
			# workspace was created by another user and does not exist on 
			# the active computer.
			workspace = ProjectWorkspace.make(job.job_num, self._app_data.users.log)
			if workspace is not None:
				job.workspace = workspace
				return True
		else:
			return True

	def _on_click_close(self, index):
		"""Serialize ``Job`` data upon ``JobFolder`` close."""
		folder = str(self.tabText(index))
		try:
			self._folders[folder].save(on_close=True)
		except (IOError, SecurityError) as error:
			if self._continue_close(error):
				# Close without saving data.
				self.close_folder(folder, index)
		else:
			self.close_folder(folder, index)
			self._status.show_save_msg(folder)

	def _continue_close(self, error):
		"""Prompt user to close ``JobFolder`` upon error.

		Parameters
		----------
		error : Exception subclass

		Returns
		-------
		True
			If user chooses to close ``JobFolder``.

		"""
		msg = error.message
		msg = [msg + '\nDo you want to continue without saving your data?']
		if Ask(type(error).__name__, msg).yes():
			return True

	def close_folder(self, job_num, index=None):
		"""Close and remove a ``JobFolder`` from ``Desk``.

		Parameters
		----------
		job_num : str
			The 6-digit job number that is associated with the ``JobFolder``.

		index : int or None
			``JobFolder`` index.
			If ``None``, the current index is retrieved.

		"""
		if index is None:
			index = self.folder_index(job_num)
		self.removeTab(index)
		del self._folders[job_num]
		self._app_data.users.log('closed job %s' % job_num)


if __name__ == '__main__':
	pass







