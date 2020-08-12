#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import getpass
import cPickle as pickle
from datetime import datetime
from gatekeeper.gatekeeper import GateKeeper
from core import Path
from work_orders import Job, WorkOrderConstants
from errors import JobNotFoundError, JobInUseError


__author__ = 'Brandon McCleary'


class JobIO:
	"""
	I/O methods designed to support the manipulation of Job objects.

	See Also
	--------
	work_orders.Job
	work_orders.Project
	work_orders.WorkOrderConstants
	gatekeeper.GateKeeper
	errors.JobNotFoundError
	errors.JobInUseError

	"""

	@staticmethod
	def job_exists(job_num):
		"""Returns True if job files were found.

		Parameters
		----------
		job_num : str
		
		Raises
		------
		OSError
			If the system cannot find the path specified.

		"""
		try:
			for f in os.listdir(Path.JOBS):
				if job_num in f:
					return True
		except OSError:
			raise

	@staticmethod
	def init_files(job_num, workspace):
		"""Create application files for a new job.

		Parameters
		----------
		job_num : str

		workspace : str
			Absolute path to the toplevel directory that stores project data.

		Returns
		-------
		True
			If files were created successfully.

		Raises
		------
		IOError
			If no such file or directory.
		
		"""
		try:
			# Create empty lockfile
			with open(os.path.join(Path.JOBS, '%s.lock' % job_num), 'wb') as f:
				pass
			# Save new Job to file
			JobIO.save(job_num, Job(job_num, workspace))
		except IOError:
			raise
		else:
			return True

	@staticmethod
	def save(job_num, job):
		"""Serialize a Job object.

		Parameters
		----------
		job_num : str

		job : Job

		Returns
		-------
		True
			If save was successful.

		Raises
		------
		IOError
			If no such file or directory.

		"""
		try:
			with open(os.path.join(Path.JOBS, '%s.nuke' % job_num), 'wb') as f:
				pickle.dump(job, f)
		except IOError:
			raise
		else:
			return True

	@staticmethod
	def get(job_num):
		"""Returns a serialized Job object.

		Parameters
		----------
		job_num : str

		Raises
		------
		IOError
			If no such file or directory.

		EOFError
			If file is empty.

		"""
		try:
			with open(os.path.join(Path.JOBS, '%s.nuke' % job_num), 'rb') as f:
				job = pickle.load(f)
		except (IOError, EOFError):
			raise
		else:
			return job

	@staticmethod
	def job_and_lock(job_num):
		"""Retrieve the objects required to perform work on a job.
		
		Parameters
		----------
		job_num : str

		Returns
		-------
		job : Job

		lock : GateKeeper
			Restricts job access to a single active user. Modifications to the 
			job must be made only while the active user has ownership.

		Raises
		------
		JobNotFoundError
		JobInUseError
		IOError
		EOFError

		Notes
		-----
		`lock` is returned in the locked state, which signifies ownership.

		"""
		if JobIO.job_exists(job_num):
			lock = GateKeeper(
				getpass.getuser(),
				os.path.join(Path.JOBS, '%s.lock' % job_num)
			)
			# Lockfile ownership check
			if lock.lock() or lock.lock_is_acquired:
				job = JobIO.get(job_num)
				return job, lock
			else:
				raise JobInUseError(lock.owner)
		else:
			raise JobNotFoundError()

	@staticmethod
	def active_job_nums():
		"""Returns a set of all active job numbers.

		Raises
		------
		OSError
			If the system cannot find the path specified.
		
		"""
		return {f[:6] for f in os.listdir(Path.JOBS)}

	@staticmethod
	def active_job_temp_files():
		"""Copy active job files and paste into temp directory.

		Returns
		-------
		temp_filename_list : list
			The filenames of all active job temp files.

		Notes
		-----
		The temp file extensions assume the active username so that there are no 
		conflicts when multiple users call this function. If a new temp file has 
		the same signature as an existing temp file, the existing temp file is 
		overridden.

		"""
		temp_filename_list = []
		user = getpass.getuser()
		for job in JobIO.active_job_nums():
			original = job + '.nuke'
			temp_file = job + '.%s' % user
			temp_filename_list.append(temp_file)
			try:
				shutil.copy(
					os.path.join(Path.JOBS, original), 
					os.path.join(Path.TEMP, temp_file)
				)
			except OSError:
				# Ignore issues raised for poor network connectivity and 
				# race conditions that arise from jobs being completed.
				pass
		return temp_filename_list

	@staticmethod
	def clear_temp_files(file_list):
		"""Remove temp files from temp directory.

		Parameters
		----------
		file_list : list
			The filenames of all temp files.

		"""
		[os.remove(os.path.join(Path.TEMP, temp_file)) for temp_file in file_list]

	@staticmethod
	def existing_projects():
		"""Retrieve the projects from all active jobs.
		
		Returns
		-------
		existing_projects : dict
			Project objects organized by their associated drawing numbers.

		"""
		existing_projects = {}
		active_job_temp_files = JobIO.active_job_temp_files()
		for filename in active_job_temp_files:
			try:
				with open(os.path.join(Path.TEMP, filename), 'rb') as job:
					temp_job = pickle.load(job)
					temp_proj = temp_job.projects
					for project in temp_proj.keys():
						existing_projects[project] = temp_proj[project]
			except OSError:
				# Ignore issues raised for poor network connectivity and 
				# race conditions that arise from jobs being completed.
				pass
		JobIO.clear_temp_files(active_job_temp_files)
		return existing_projects

	@staticmethod
	def sort_project_data(project_dict):
		"""Organize a dictionary of Project objects by job number.

		Parameters
		----------
		project_dict : dict
			A collection of Project objects organized by drawing number.

		Returns
		-------
		job_dict : dict
			Contains job number keys and lists of Project objects as values.

		Notes
		-----
		The Project objects lose their corresponding drawing numbers during
		the transfer to job_dict.

		"""
		job_dict = {}
		try:
			for project in project_dict.keys():
				try:
					job_dict[project[:6]].append(project_dict[project])
				except KeyError:
					job_dict[project[:6]] = []
					job_dict[project[:6]].append(project_dict[project])
		except AttributeError:
			return job_dict
		else:
			return job_dict

	@staticmethod
	def jobs_at_a_glance(job_dict):
		"""Get a summarized report of active job data.

		Parameters
		----------
		job_dict : dict
			See JobIO.sort_project_data.

		Returns
		-------
		jobs : dict
			A dictionary of dictionaries comprised of project due date 
			information and organized by job number. Nested keys include
			'expired' (past due), 'today' (due today), and 'approaching' (due
			within 2 days). Nested values are the integer number of Project
			objects whose due dates fall within the key category.

		"""
		jobs = {}
		completed = WorkOrderConstants.STATUS_LIST[-1]

		# Get a reference for today's date to check against project due dates.
		now = datetime.strptime(datetime.now().strftime('%m/%d/%Y'), '%m/%d/%Y')

		for job in job_dict.keys():
			expired = 0
			today = 0
			approaching = 0
			for project in job_dict[job]:
				if project.status != completed:  # Ignore completed projects
					due_date = datetime.strptime(project.due_date, '%m/%d/%Y')
					delta = (due_date - now).days
					if delta < 0:
						expired += 1
					elif delta == 0:
						today += 1		
					elif delta < 3:
						approaching +=1

			jobs[job] = {
				'expired' : expired,
				'today' : today,
				'approaching' : approaching
			}
		return jobs

	@staticmethod
	def drawing_nums_from_job(job):
		"""Return the list of drawing numbers in a Job object."""
		return [proj for proj in job.projects.keys() if JobIO.is_dwg_num(proj)]

	@staticmethod
	def drawing_nums_from_list(items):
		"""Return the list of drawing numbers found in a list of items."""
		return [item for item in items if JobIO.is_dwg_num(item)]

	@staticmethod
	def is_dwg_num(text):
		"""Returns True if text string is in the drawing number format."""
		return text.count('-') == 3

	@staticmethod
	def clear_job_files(job_num):
		"""Delete the files associated with a job number.

		Parameters
		----------
		job_num : str

		Returns
		-------
		True
			If 2 job files (.nuke, .lock) were deleted.

		Raises
		------
		OSError
			If the system cannot find the path specified.

		"""
		file_count = 2
		for f in os.listdir(Path.JOBS):
			if job_num in f:
				os.remove(os.path.join(Path.JOBS, f))
				file_count -= 1
				if file_count == 0:
					return True

	@staticmethod
	def job_due_date(job):
		"""Get the latest due date from a job's projects.

		Parameters
		----------
		job : Job

		Returns
		-------
		str
			Per WorkOrderConstants.DATE_FORMAT. If no project due dates are 
			found, 'not found' is returned.
		
		"""
		NOT_FOUND_MSG = 'not found'
		format = WorkOrderConstants.DATE_FORMAT
		proj_dates = []
		try:
			for proj in job.projects.keys():
				proj_dates.append(datetime.strptime(job.projects[proj].due_date, 
					format))
		except (AttributeError, ValueError):
			# proj_dates is an empty list.
			return NOT_FOUND_MSG
		else:
			return datetime.strftime(max(proj_dates), format)

	@staticmethod
	def move(src, dst_dir):
		"""Move a file to a different directory.

		Parameters
		----------
		src : str
			Absolute file path.
		
		dst_dir : str
			Absolute path to destination directory.

		Raises
		------
		IOError
			Source file open by another process or file not found.

		"""
		path, filename = os.path.split(src)
		dst = os.path.join(dst_dir, filename)
		shutil.move(src, dst)



if __name__ == '__main__':
	pass