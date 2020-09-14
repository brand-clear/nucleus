#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
from collections import OrderedDict
from PyQt4 import QtGui
from pywinscript.msoffice import send_email
from pyqtauto.widgets import (MenuBar, ExceptionMessageBox, Ask, Dialog, 
	ImageButton, Spacer, GenericButton)
from sulzer.extract import Extract
from work_orders import WorkOrderConstants
from core import Image, Path
from job_io import JobIO
from errors import (JobNumberError, ExistingJobError, WorkspaceError, 
	JobInUseError)


__author__ = 'Brandon McCleary'


class MenuView(MenuBar):
	"""
	The graphical interface to menubar commands.

	Attributes
	----------
	file_menu : QMenu
	view_menu : QMenu
	admin_menu : QMenu
	new : QAction
	open : QAction
	save : QAction
	complete : QAction
	add_qc_stp : QAction
	add_dxf : QAction
	upload_data : QAction
	about : QAction
	version : QAction

	"""
	def __init__(self, parent):
		super(MenuView, self).__init__(parent)
		# File menu
		self.file_menu = self.add_menu('File')
		self.new = self.add_action(self.file_menu, Image.NEW_JOB, 'New', 
			'Ctrl+N')
		self.open = self.add_action(self.file_menu,	Image.OPEN,	'Open',	
			'Ctrl+O')
		self.save = self.add_action(self.file_menu, Image.SAVE, 'Save', 
			'Ctrl+S')
		self.complete = self.add_action(self.file_menu, Image.COMPLETE, 
			'Complete', 'Ctrl+1')
		self.view_menu = self.add_menu('View')
		self.active_projects = self.add_action(self.view_menu, Image.ACTIVE,
			'Active Projects', 'Ctrl+2')

		# Admin menu
		self.admin_menu = self.add_menu('Admin')
		self.upload_data = self.add_action(self.admin_menu, Image.UPLOAD,
			'Upload WC Data', 'Ctrl+U')

		# About menu
		self._info_menu = self.add_menu('Info')
		self.about = self.add_action(self._info_menu, Image.ABOUT, 'About')
		self.version = self.add_action(self._info_menu, Image.VERSION, 
			'Versions')


class NewJobRequest(object):
	"""
	Handles a request to create new job files and directories in ``Nucleus``.
	
	Parameters
	----------
	job_num : str
		The 6-digit job number.

	logger : logging.getLogger
		Sends informative messages to user log file.

	See Also
	--------
	errors.JobNumberError
	errors.ExistingJobError
	errors.WorkspaceError
	menu.ProjectWorkspace
	job_io.JobIO
	
	"""
	def __init__(self, job_num, logger):
		self._job_num = job_num
		self._logger = logger

	def approved(self):
		"""Evaluate a new job request.

		Returns
		-------
		True
			If job files were created successfully.

		Raises
		------
		JobNumberError
		ExistingJobError
		WorkspaceError
		OSError
		IOError

		"""
		self._validate_job_num()
		self.workspace = ProjectWorkspace.make(self._job_num, self._logger)
		if self.workspace is not None:
			return JobIO.init_files(
				self._job_num, 
				self.workspace
			)
				
	def _validate_job_num(self):
		"""Confirm that a job number is valid and does not already exist.

		Raises
		------
		JobNumberError
		ExistingJobError
		OSError

		"""
		if len(self._job_num) != 6:
			raise JobNumberError()
		elif JobIO.job_exists(self._job_num):
			raise ExistingJobError()


class ProjectWorkspace:
	"""
	Provides methods to create a project workspace.

	Within each ``Job`` is a directory path that ends with the job number. This 
	directory, called the workspace, contains subdirectories that will store 
	and organize all active project files related to the ``Job``.

	See Also
	--------
	work_orders.Job

	"""
	# Define the subdirectory layout
	_STRUCTURE = OrderedDict()
	_STRUCTURE['Layouts'] = None
	_STRUCTURE['Programming'] = None
	_STRUCTURE['Rotating'] = {
		'Blading': None,
		'Disks': 'Stage 1',
		'Impellers': 'Stage 1',
		'Other': None,
		'Rotors': None,
		'Shafts': None,
		'Sleeves': None
	}
	_STRUCTURE['Stationary'] = {
		'Case': None,
		'Diaphragms': 'Stage 1',
		'Housings': None,
		'IGVs': 'Stage 1',
		'Other': None
	}

	@classmethod
	def init_workspace(cls, workspace):
		"""Create the project workspace subdirectory structure.

		Parameters
		----------
		workspace : str
			The top-level project workspace directory.

		Notes
		-----
		If some directories already exist, this method will create the missing
		directories.

		"""
		# Top level dirs
		for k in cls._STRUCTURE.keys():
			try:
				os.mkdir(os.path.join(workspace, k))
			except OSError:
				pass

			# Next level dirs
			if cls._STRUCTURE[k] is not None:
				for j in cls._STRUCTURE[k].keys():
					try:
						os.mkdir(os.path.join(workspace, k, j))
					except OSError:
						pass

					# Last level dirs
					if cls._STRUCTURE[k][j] is not None:
						try:
							os.mkdir(
								os.path.join(
									workspace, k, j, cls._STRUCTURE[k][j]
									)
								)
						except OSError:
							pass

	@staticmethod
	def get_toplevel_workspace():
		"""Prompt the user to select a top-level project workspace directory.
		
		Returns
		-------
		str or None
			The selected project workspace directory.

		bool
			True if the user made a selection, False if the user cancelled.

		"""
		dialog = QtGui.QFileDialog(
			caption='Select Project Workspace', 
			directory=Path.VAULT
		)
		dialog.setFileMode(QtGui.QFileDialog.DirectoryOnly)
		if dialog.exec_():
			return str(dialog.selectedFiles()[0]), True
		else:
			return None, False

	@staticmethod
	def make(job_num, logger):
		"""Create a valid project workspace.

		Parameters
		----------
		job_num : str
			A 6-digit integer that is associated with a collection of work 
			orders.

		logger : logging.getLogger
			Sends informative messages to user log file.

		Returns
		-------
		workspace : str or None
			A validated project workspace directory.
		
		"""
		while True:
			workspace, ok = ProjectWorkspace.get_toplevel_workspace()
			if ok:
				if os.path.basename(workspace) == job_num:
					ProjectWorkspace.init_workspace(workspace)
					logger('set %s workspace' % job_num)
					return workspace
				else:
					ExceptionMessageBox(WorkspaceError()).exec_()
			else:
				return


class CompleteJobRequest(object):
	"""
	Handles a request to remove job files from Nucleus.

	Parameters
	----------
	job_num : str

	recipients : list
		Email addresses that will receive confirmation email.

	job : Job or None, optional
		
	lock : GateKeeper, optional
		Controls read and write access to job applicaton files.

	Attributes
	----------
	dwg_count : int
		The number of drawings found in the job. This value is logged to file if
		the request is approved.

	"""
	def __init__(self, job_num, recipients, job=None, lock=None):
		self._job_num = job_num
		self._to = recipients
		self._job = job
		self._lock = lock
		self._retain_ownership = False if self._job is None else True
		self.dwg_count = None
		self.projects = []

	def approved(self):
		"""Evaluate the complete job request.
		
		Returns
		-------
		True
			If job files were removed successfully.

		Raises
		------
		JobInUseError
		IOError
		EOFError
		ProjectsFolderRootError
		DestinationError

		"""
		self._verify_job()
		dwg_nums = JobIO.drawing_nums_from_job(self._job)
		self.dwg_count = len(dwg_nums)
		pdf_dir = Extract.issued_prints_folder(self._job_num)
		self._bulk_pdf_transfer(pdf_dir)
		msg = self._get_document_control_msg(dwg_nums, pdf_dir)

		if Ask('Confirm', msg).yes():
			self._close(msg)
			return True
		else:
			if not self._retain_ownership:
				self._lock.unlock()

	def _verify_job(self):
		"""Confirm that an active job is acquired."""
		if self._job is None:
			try:
				self._job, self._lock = JobIO.job_and_lock(self._job_num)
			except (JobInUseError, IOError, EOFError):
				raise
		self.projects = self._job.projects

	def _incomplete_project_count(self, dwg_nums):
		"""Count the number of incomplete Project objects.

		Parameters
		----------
		dwg_nums : list

		Returns
		-------
		count : int

		"""
		count = 0
		completed = WorkOrderConstants.STATUS_LIST[-1]
		for dwg_num in dwg_nums:
			if self._job.projects[dwg_num].status != completed:
				count += 1
		return count

	def _get_file_count(self, path):
		"""Count the number of job files in a directory.

		Parameters
		----------
		path : str

		Returns
		-------
		count : int

		"""
		count = 0
		for f in os.listdir(path):
			if self._job_num in f:
				count += 1
		return count

	def _get_document_control_msg(self, dwg_nums, pdf_dir):
		"""Generate a message that quantifies how many job files exist.

		Parameters
		----------
		dwg_nums : list
		pdf_dir : string

		Returns
		-------
		msg : list

		"""
		incomplete = self._incomplete_project_count(dwg_nums)
		pdfs = self._get_file_count(pdf_dir)
		stps = self._get_file_count(Path.QC_MODELS)
		msg = ['Drawings found: %d' % self.dwg_count]
		msg.append('Drawings not completed: %d' % incomplete)
		msg.append('Non-controlled PDF files found: %d' % pdfs)
		msg.append('Quality control STEP files found: %d\n' % stps)
		msg.append(
			'Do you want to continue completing this job? This cannot be undone.'
		)
		return msg

	def _close(self, msg):
		"""Remove job files and send confirmation email.

		Parameters
		----------
		msg : list
			Document control message.
		
		"""
		if JobIO.clear_job_files(self._job_num):
			msg.append('Yes')
			send_email(self._to, [], '%s Completed' % self._job_num, 
				'<br>'.join(msg), True)

	def _bulk_pdf_transfer(self, dst):
		"""Move PDF files from job workspace to issued prints folder.

		Parameters
		----------
		dst: str
			Absolute path to the issued prints folder.

		"""
		for root, dirs, files in os.walk(self._job.workspace):
			for filename in files:
				if os.path.splitext(filename)[1] == '.pdf':
					JobIO.move(os.path.join(root, filename), dst)


class AboutDialog(Dialog):
	"""
	Presents a general description of ``Nucleus`` and allows the user to contact
	the developer directly.

	"""
	def __init__(self):
		# Build GUI
		super(AboutDialog, self).__init__('About', 'QFormLayout')
		self._intro = '' \
			'Nucleus is a Sulzer software application that aims to track, \n' \
			'schedule, and optimize the work performed by the CAD \n' \
			'Department at Sulzer RES La Porte. \n\n' \
			'Nucleus is developed and maintained by Brandon McCleary \n' \
			'with input from other Sulzer members. '
		self._icon_btn = ImageButton(
			Image.LOGO,
			response=self._on_click_contact,
			flat=True
		)
		self._icon_btn.myheight = 100
		self.layout.addRow(QtGui.QLabel(self._intro), self._icon_btn)
		self._outro = 'Questions or suggestions for future Nucleus versions?'
		self._contact_btn = GenericButton(
			'Contact',
			response=self._on_click_contact
		)
		self.layout.addRow(QtGui.QLabel(self._outro), self._contact_btn)
		self.setMaximumSize(self.width(), self.height())

	def _on_click_contact(self):
		"""Initiate email to ``Nucleus`` developer."""
		send_email(
			['brandon.mccleary@sulzer.com'], [], 'Regarding Nucleus', '', True
		)


if __name__ == '__main__':
	import sys
	app = QtGui.QApplication(sys.argv)
	AboutDialog().exec_()
