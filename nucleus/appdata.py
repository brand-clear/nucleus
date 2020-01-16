#!/usr/bin/env python
# -*- coding: utf-8 -*-
import errno
import logging
import os.path
import getpass
from datetime import datetime
import pandas as pd
from core import Path
from job_io import JobIO
from work_orders import WorkOrderConstants


__author__ = 'Brandon McCleary'


class AppData(object):
	"""
	Loads, organizes, and distributes core application data.

	Parameters
	----------
	path : str
		Absolute path to the application data XLSX file.

	Raises
	------
	IOError
		If no such file or directory is found.
	EOFError
		If file is empty.

	See Also
	--------
	appdata.UserData
	appdata.NamingConvention
	appdata.Templates

	"""
	def __init__(self, path):
		super(AppData, self).__init__()
		try:
			self._df = pd.read_excel(path, None)
			self._users = UserData(self._df['Users'])
			self._naming_convention = NamingConvention(
				self._df['PartConvention'],
				self._df['ProcessConvention'],
				self._df['DetailConvention']
			)
			self._templates = Templates(self._df['Templates'])
			self._agreements = self._df['UserAgreement']
		except (IOError, EOFError):
			raise

	@property
	def df(self):
		"""A ``DataFrame`` containing all core application data."""
		return self._df

	@property
	def users(self):
		"""UserData: Application user data."""
		return self._users
	
	@property
	def naming_convention(self):
		"""NamingConvention: The drawing naming convention library."""
		return self._naming_convention

	@property
	def templates(self):
		"""Templates: The drawing template library."""
		return self._templates

	@property
	def agreements(self):
		"""Agreements: The description of user responsibilities."""
		return self._agreements


class NamingConvention(object):
	"""
	A library of naming convention standards for CAD drawings at Sulzer RES.

	CAD drawing numbers are divided into 3 sections (excluding the job number) 
	joined by a '-'. 

		Section 1) A part name (4 alpha characters)
		Section 2) A process name (3 alpha characters)
		Section 3) Any additional, valuable detail (2-4 alphanumeric characters)

	For example:

		DEFR-MFG-00 or DEFR-MFG-TECE

	Each section of the drawing number uses an approved abbreviation of the 
	actual word. Throughout ``NamingConvention``, 'names' will correspond to the 
	actual words and 'convention' will correspond to the abbreviations.

	Parameters
	----------
	part_df : DataFrame
		Contains part naming convention standards.
		Required columns: {'Name', 'Convention'}

	process_df : DataFrame
		Contains process naming convention standards.
		Required columns: {'Name', 'Convention'}

	detail_df : DataFrame
		Contains detail naming convention standards.
		Required columns: {'Name', 'Convention'}

	Attributes
	----------
	part_names : list
	process_names : list
	detail_names : list

	"""
	def __init__(self, part_df, process_df, detail_df):
		self._part_df = part_df
		self._process_df = process_df
		self._detail_df = detail_df
		self._map = {
			'part': self._part_df,
			'process': self._process_df,
			'detail': self._detail_df
		}

	@property
	def part_names(self):
		"""list: Part names for section 1 of the drawing number."""
		return self._get_names('part')

	@property
	def process_names(self):
		"""list: Process names for section 2 of the drawing number."""
		return self._get_names('process')

	@property
	def detail_names(self):
		"""list: Detail names for section 3 of the drawing number."""
		return self._get_names('detail')

	def _get_names(self, convention_type):
		"""Get names for parts, processes, or details.

		Parameters
		----------
		convention_type : {'part', 'process', 'detail'}

		Returns
		-------
		list
			Names of a given `convention_type`.

		"""
		return self._map[convention_type]['Name'].tolist()

	def get_convention(self, convention_type, name):
		"""Get the convention of a given part, process, or detail.

		Parameters
		----------
		convention_type : {'part', 'process', 'detail'}

		name : str
			The name of a part, process, or detail that is related to a drawing 
			number.

		Returns
		-------
		str
			The convention for `name`.

		Raises
		------
		IndexError
			If `name` does not find a matching `convention_type` abbreviation.
		
		"""
		df = self._map[convention_type]
		return df['Convention'][df['Name'] == name].values[0]

	def valid_custom_input(self, convention_type, text):
		"""Check a custom input for conformity to convention standards.

		Parameters
		----------
		convention_type : {'part', 'process', 'detail'}

		text : str
			Custom naming convention suggestion.

		Returns
		-------
		True
			If `text` conforms to `convention_type` convention.

		"""
		if convention_type == 'part':
			if len(text) == 4 and text.isalpha():
				return True
		elif convention_type == 'process':
			if len(text) == 3 and text.isalpha():
				return True
		elif convention_type == 'detail':
			if len(text) >= 2 and len(text) <= 4:
				return True


class Templates(object):
	"""
	A library of CAD template data at Sulzer RES.

	Parameters
	----------
	df : DataFrame
		Contains CAD template data.
		Required columns: {'Name', 'Clearance', 'Interference', 'Other'}

	Attributes
	----------
	clearance_templates : list
	interference_templates : list
	other_templates : list

	"""
	def __init__(self, df):
		self._df = df

	@property
	def clearance_templates(self):
		"""list: Clearance-based CAD template names."""
		return self._df['Name'][self._df['Clearance'] == 1.0].tolist()

	@property
	def interference_templates(self):
		"""list: Interference-based CAD template names."""
		return self._df['Name'][self._df['Interference'] == 1.0].tolist()

	@property
	def other_templates(self):
		"""list: CAD template names that are not fit-based."""
		return self._df['Name'][self._df['Other'] == 1.0].tolist()

	def template_setlist(self, *args):
		"""Get every unique value from one or more ``list`` objects.

		Parameters
		----------
		args : list

		Returns
		-------
		list
			All unique values from `args` in alphabetical order.

		"""
		temp_list = []
		for a in args:
			temp_list += a
		return sorted(list(set(temp_list)))

	def template_image(self, template_name):
		"""Get a template's HTML image tag.

		Parameters
		----------
		template_name : str
			Basename of a template file, excluding extension.
		
		Returns
		-------
		str
			HTML image tag corresponding to `template_name`.

		"""
		filepath = os.path.join(Path.TEMPLATES, template_name + '.png')
		return '<img src="%s">' % filepath


class UserData(object):
	"""
	Represents a database of user information.

	Each registered user is allocated a specific folder that, over time, is 
	populated with logging and statistical information. This folder is created 
	or confirmed each time the user logs in.

	Parameters
	----------
	df : DataFrame
		Required columns: {'Username', 'Name', 'Level', 'Email', 'Probe Sub'}
		'Level' options: {'Supervisor', 'Technician', 'Admin'}
		'Probe Sub' options: {'To', 'Cc', ''}

	Attributes
	----------
	df
	my_username
	my_name
	my_level
	my_folder
	usernames
	technician_names
	my_projects
	my_job_data
	my_jobs_at_a_glance
	supervisor_email_addresses

	Raises
	------
	OSError
		If the system cannot find `my_folder`.

	"""
	def __init__(self, df):
		self._df = df
		self._my_username = getpass.getuser()
		self._init_user_folder()
		self._init_log_file()
		self.log('logged in')

	def _init_user_folder(self):
		"""Ensure the active user's folder exists.
		
		Raises
		------
		OSError
			If the system cannot find the path specified.

		"""
		# Registered users have their own folder, unregistered users share one.
		if self.my_name is not None:
			self._my_folder = os.path.join(Path.USERS, self._my_username)
		else:
			self._my_folder = os.path.join(Path.USERS, 'unregistered')

		try:
			os.mkdir(self._my_folder)
		except OSError as error:
			if error.errno == errno.EEXIST:
				# Folder already exists
				pass
			else:
				raise error

	def _init_log_file(self):
		"""Ensure the active user's logfile exists."""
		# A new log file is created each month.
		logfile = '%s %s.log' % (
			self.my_username, 
			datetime.now().strftime('%Y-%m')
		)
		# Set log filepath.
		logpath = os.path.join(self._my_folder, logfile)

		# Set logger properties.
		formatter = logging.Formatter('%(asctime)s  %(levelname)s: %(message)s')
		file_handler = logging.FileHandler(logpath)
		file_handler.setFormatter(formatter)
		self._logger = logging.getLogger('user')
		self._logger.setLevel(logging.INFO)
		self._logger.addHandler(file_handler)

	@property
	def df(self):
		"""DataFrame: The entire user data source."""
		return self._df

	@property
	def my_username(self):
		"""str: Username of the active user."""
		return self._my_username

	@property
	def my_name(self):
		"""str or None: Given name of the active user.
		
		If ``None``, the active user is not registered.
		
		"""
		return self.get_users_name(self.my_username)

	@property
	def my_level(self):
		"""str or None: User level of the active user.
		
		If ``None``, the active user is not registered.
		
		"""
		try:
			level = self._df['Level'][self._df['Username'] == self._my_username]
			return level.tolist()[0]
		except IndexError:
			return

	@property
	def my_folder(self):
		"""str: User folder for the active user."""
		return self._my_folder

	@property
	def usernames(self):
		"""list: The collection of registered usernames."""
		drop_nans = self._df[self._df['Username'].notnull()]
		return drop_nans['Username'].tolist()

	@property
	def technician_names(self):
		"""list: The collection of given 'Technician' names."""
		techs = self._df['Name'][self._df['Level'] == 'Technician'].tolist()
		techs.append('Brandon')
		return techs

	@property
	def supervisor_email_addresses(self):
		"""list: Email addresses for all users of 'Level' 'Supervisor'."""
		return self._df['Email'][self._df['Level'] == 'Supervisor'].tolist()

	@property
	def my_projects(self):
		"""dict: A collection of ``Projects`` owned by the active user and 
		organized by drawing number.

		"""
		my_projects = {}
		if self.my_name is None:
			my_projects

		existing_projects = JobIO.existing_projects()
		for project in existing_projects.keys():
			if existing_projects[project].owner == self.my_name:
				my_projects[project] = existing_projects[project]
		return my_projects

	@property
	def my_job_data(self):
		"""dict: ``lists`` of ``Projects`` owned by the active user and
		organized by job number.
		
		Notes
		-----
		These ``Projects`` are no longer linked with their corresponding
		drawing numbers.

		"""
		return JobIO.sort_project_data(self.my_projects)

	@property
	def my_jobs_at_a_glance(self):
		"""dict: ``dicts`` comprised of due date information for the active 
		user's projects organized by job number.

		Nested keys: 
		'expired' (past due), 'today' (due today), and 'approaching' 
		(due within 2 days). 
		
		Nested values (``int``): 
		The number of ``Projects`` whose due dates fall within the key category.

		"""
		# LEAD was introduced to provide the drafting lead with a glance at
		# all department projects, not just his/her own. LEAD is still 
		# classified with a user level of 'Technician' so that he or she can be
		# assigned projects, which is an option 'Supervisor' users do not have.
		LEAD = 'Jaye'

		if self.my_level == 'Supervisor' or self.my_name == LEAD:
			# Supervisors and leads are linked with all jobs.
			return JobIO.jobs_at_a_glance(
				JobIO.sort_project_data(JobIO.existing_projects())
			)
		elif self.my_level == 'Technician':
			return JobIO.jobs_at_a_glance(self.my_job_data)

	def get_users_name(self, username):
		"""Get the name associated with a given username.

		Parameters
		----------
		username : str

		Returns
		-------
		str or None
			The given name associated with `username`. If ``None``, `username`
			is not a registered user.
		
		"""
		try:
			return self.df['Name'][self.df['Username'] == username].tolist()[0]
		except IndexError:
			return

	def log(self, msg):
		"""Send an informative message ``str`` to user log file."""
		self._logger.info('%s ~ %s' % (self.my_username, msg))

	def probe_email_addresses(self, field):
		"""Get the addresses of probe location email recipients.
		
		Parameters
		----------
		field : {'To', 'Cc'}

		Returns
		-------
		list
			Email addresses in `field` section.
		
		"""
		return self._df[self._df['Probe Sub'] == field]['Email'].tolist()


if __name__ == '__main__':
	print help(UserData)
