#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module contains custom ``Exception`` subclasses for the ``Nucleus``
application.

"""
from pyqtauto.widgets import OrphanMessageBox


__author__ = 'Brandon McCleary'


class TryAgainBaseError(Exception):
	def __init__(self, error_msg):
		self.message = error_msg + ' Try again.'


class WorkspaceError(TryAgainBaseError):
    def __init__(self):
		super(WorkspaceError, self).__init__(
			'The project workspace path must end with a matching job number.'
		)


class JobNumberError(TryAgainBaseError):
    def __init__(self):
		super(JobNumberError, self).__init__(
			'The job number must be a 6-digit integer.'
		)


class ExistingJobError(Exception):
	def __init__(self):
		self.message = 'The job you are trying to create already exists. Try '\
			'opening the existing job.'


class UnknownError(TryAgainBaseError):
    def __init__(self):
		super(UnknownError, self).__init__(
			'An unknown error has occurred.'
		)


class JobNotFoundError(Exception):
    def __init__(self):
		self.message = 'The job you are trying to open cannot be found. Check '\
			'the job number and try again.'


class JobInUseError(Exception):
    def __init__(self, user):
		self.message = 'The job you are trying to open is locked by user '\
			"'%s'." % user


class StartUpError(Exception):
	def __init__(self):
		self.message = 'The application data you are requesting is temporarily'\
			' unavailable. If this problem continues, contact admin.'


class ColumnError(Exception):
	def __init__(self, cols):
		formatted_cols = '\n'.join(cols)
		self.message = 'The document supporting this process does not contain '\
			'the following required columns:\n%s' % formatted_cols


class EmptyModelError(Exception):
	def __init__(self):
		self.message = 'No unassigned jobs were found.'
		self.icon = 'information'


class InvalidDatesError(Exception):
	def __init__(self, indices):
		self.indices = indices


class PasswordError(TryAgainBaseError):
	def __init__(self):
		super(PasswordError, self).__init__('Incorrect password.')
		

class InputError(TryAgainBaseError):
	def __init__(self):
		super(InputError, self).__init__('Invalid input.')


class DrawingNumberError(TryAgainBaseError):
	def __init__(self):
		super(DrawingNumberError, self).__init__(
			'The drawing number you entered does not conform to the ' \
				'established naming convention.'
		)


class ProjectStorageError(TryAgainBaseError):
	def __init__(self):
		super(ProjectStorageError, self).__init__(
			'No project storage directory was selected.'
		)


class TemplateError(TryAgainBaseError):
	def __init__(self):
		super(TemplateError, self).__init__('No template file was selected.')


class AliasNumberError(TryAgainBaseError):
	def __init__(self):
		super(AliasNumberError, self).__init__(
			'The alias number you entered does not conform to convention.'
		)


class ProjectNoteError(TryAgainBaseError):
	def __init__(self):
		super(ProjectNoteError, self).__init__(
			'No project note was entered.'
		)


class SecurityError(Exception):
	def __init__(self):
		self.message = 'The rights to the job you are trying to save belong ' \
			'to another user.'
		self.icon = 'critical'


class MultipleJobError(TryAgainBaseError):
	def __init__(self):
		super(MultipleJobError, self).__init__(
			'Only one job may be modified at a time.'
		)


class MissingPDFError:

	@classmethod
	def show(cls, pdfs):
		message = ['The following non-controlled PDFs could not be found:']
		for pdf in pdfs:
			message.append(pdf)
		OrphanMessageBox(cls.__name__, message, 'information').exec_()

		