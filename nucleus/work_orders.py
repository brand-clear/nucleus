#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This modules provides objects that represent the work received by the CAD 
department at Sulzer RES La Porte.

"""
from datetime import datetime, timedelta
from collections import OrderedDict


__author__ = 'Brandon McCleary'


class WorkOrderConstants:
	
	STATUS_LIST = [
		'Unassigned',
		'In Process',
		'On Hold',
		'At Review',
		'Completed'
	]

	DATE_FORMAT = '%m/%d/%Y'


class Job(object):
	"""
	Represents a collection of work orders billed to a single customer.

	The work orders are collectively linked to a 6-digit integer known as the 
	job number, which is used to distinguish one ``Job`` from another.

	Parameters
	----------
	job_num : str
		The 6 digit integer associated with this collection of work orders.
	workspace : str
		A particular 'Vault WorkSpace' subdirectory corresponding to `job_num`.

	Attributes
	----------
	job_num : str
	workspace : str
	projects : dict{str : Project}
		Contains ``Project`` objects (values) that each correspond to a single 
		work order. Each ``Project`` can be referenced by its corresponding 
		work order identifier (key).

	Notes
	-----
	Throughout the lifecycle of an instance of ``Job``, the key pertaining to 
	each ``Project`` object can be changed by the user to instead reference an 
	associated drawing name.

	"""
	def __init__(self, job_num, workspace):
		self.job_num = job_num
		self.workspace = workspace
		self.projects = {}

	def add_project(
		self, alias_num, work_instructions, owner, due_date, status='Unassigned'
		):
		"""
		Parameters
		----------
		alias_num : str
			Unique work order identifier used to track posted man hours.
		work_instructions : str
			Description of work order.
		owner : str
			User that is responsible for completing work order.
		due_date : str
			Work order deadline.
		status : str
			In accordance with WorkOrderConstants.STATUS_LIST, optional

		"""
		self.projects[alias_num] = Project(
			alias_num, work_instructions, owner, due_date, status
		)


class Project(object):
	"""
	Represents a released work order.

	In the context of the CAD department, a work order is related to either a 
	reverse engineering task or drawing.

	Parameters
	----------
	alias_num : str
		Unique work order identifier used to track posted man hours.
	work_instructions : str
		Description of work order.
	owner : str
		User that is responsible for completing work order.
	due_date : str
		Work order deadline.
	status : str
		In accordance with WorkOrderConstants.STATUS_LIST, optional

	Attributes
	----------
	alias_num : str
	owner : str
	due_date : str
	status : str
	notes : NoteDict
		Contains work order documentation as values, and signatures including 
		the date, time, and author, as keys. The order of key, value pairs is 
		chronological.

	"""
	def __init__(self, alias_num, work_instructions, owner, due_date, 
			status='Unassigned'):
		self.alias_num = alias_num
		self.owner = owner
		self.due_date = due_date
		self.status = status
		self.notes = NoteDict(work_instructions)


class NoteDict(object):
	"""
	Represents a dictionary of notes (values) ordered chronologically by the 
	date and time at which each note is created (keys). 
	
	Parameters
	----------
	note : str
		Descriptive text.

	Notes
	-----
	New instances are initialized with 'Work Instructions' as the first key.

	"""
	def __init__(self, note):
		self._data = OrderedDict()
		self._data['Work Instructions'] = note

	@property
	def data(self):
		return self._data


	def add(self, note, author):
		"""Add a new key, value pair to ``NoteDict``.

		Parameters
		----------
		note : str
			Descriptive text.
		author : str
			Creator of `note`.

		"""
		stamp = '%s by %s' % (self.timestamp(), author)
		self._data[stamp] = note
	
	def timestamp(self):
		"""Returns the current date and time as a ``str``.
		
		Notes
		-----
		Return value in '02/13/2019 @ 04:45:06 PM' format.
		
		"""
		return datetime.now().strftime('%m/%d/%Y @ %I:%M:%S %p')


if __name__ == '__main__':
	pass