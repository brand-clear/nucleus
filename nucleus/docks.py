#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import xlrd
import pandas as pd
from collections import OrderedDict
from PyQt4 import QtGui, QtCore
from pyqtauto.widgets import ImageButton, Table, TableItem
from context import RosterContextMenu
from core import Image, Path


__author__ = 'Brandon McCleary'


class PartLocator(object):
	"""
	Represents a searchable database of part storage locations.

	Parameters
	----------
	xlsx_path : str
		Absolute path to the spreadsheet containing part storage locations.

	Attributes
	----------
	view : PartLocatorView

	"""
	def __init__(self, xlsx_path):
		self._xlsx_path = xlsx_path
		self._wb = {}
		self.view = PartLocatorView()
		try:
			# Get DataFrames from XLSX sheets
			self._wb['Job Bins'] = pd.read_excel(
				self._xlsx_path, 'Job Bins', header=1
			)
			self._wb['Pallet Racks'] = pd.read_excel(
				self._xlsx_path, 'Pallet Racks', header=1
			)
			self._wb['Shaft Racks'] = pd.read_excel(
				self._xlsx_path, 'Shaft Racks', header=1
			)
		except IOError:
			# XLSX path unavailable
			self.view.disable()
		else:
			self._actions = PartLocatorActions(self._wb)
			self.view.search_btn.clicked.connect(self._on_click_search)
			self.view.search_le.returnPressed.connect(self._on_click_search)

	def _on_click_search(self):
		"""Update view with search data."""
		self.view.results.setRowCount(0)
		try:
			# Confirm value was entered.
			text = int(self.view.search_le.text())
		except ValueError:
			return
		else:
			self._set_table(self._actions.search_results(text))

	def _set_table(self, results):
		"""Fill the view ``Table`` with search results.

		Parameters
		----------
		results : dict
			Keys : {'Job Bins', 'Pallet Racks', 'Shaft Racks'}
			Values : list
				Search results.

		"""
		result_count = self._actions.max_value_len(results)
		self.view.results.setRowCount(result_count)
		for i in range(result_count):
			self.view.set_table_col(
				results['Job Bins'], 
				self._actions.sheet_col_map.keys().index('Job Bins')
			)
			self.view.set_table_col(
				results['Pallet Racks'], 
				self._actions.sheet_col_map.keys().index('Pallet Racks')
			)
			self.view.set_table_col(
				results['Shaft Racks'], 
				self._actions.sheet_col_map.keys().index('Shaft Racks')
			)


class PartLocatorView(QtGui.QDockWidget):
	"""
	A dockable interface that users can query to find part storage locations.

	Attributes
	----------
	search_le : QLineEdit
	search_btn : ImageButton
	results : Table

	"""
	def __init__(self):
		# Build GUI
		super(PartLocatorView, self).__init__('Part Locator')
		self._widget = QtGui.QWidget()
		self._v_layout = QtGui.QVBoxLayout(self._widget)
		self._h_layout = QtGui.QHBoxLayout()
		self._search_lb = QtGui.QLabel('Job Number:')
		self._h_layout.addWidget(self._search_lb)
		self.search_le = QtGui.QLineEdit()
		self.search_le.setValidator(QtGui.QIntValidator())
		self.search_le.setMaxLength(6)
		self._h_layout.addWidget(self.search_le)
		self.search_btn = ImageButton(Image.SEARCH, self._h_layout, flat=True)
		self._v_layout.addLayout(self._h_layout)
		self.results = Table(['Bins', 'Pallets', 'Racks'])
		self.results.verticalHeader().setVisible(False)
		self._v_layout.addWidget(self.results)
		self.setWidget(self._widget)

	def disable(self):
		self.setEnabled(False)

	def set_table_col(self, values, col):
		"""Fill a ``Table`` column.

		Parameters
		----------
		values : list
			Items used to fill column.

		col : int
			``Table`` column index.

		"""
		for i in range(len(values)):
			try:
				# For job bins (search values return floats, must convert to str)
				self.results.setItem(i, col, TableItem(str(int(values[i]))))
			except ValueError:
				# For pallet/shaft racks
				self.results.setItem(i, col, TableItem(values[i]))


class PartLocatorActions(object):
	"""
	Responsive actions to ``PartLocatorView`` triggers.

	Parameters
	----------
	wb : dict
		Keys : {'Job Bins', 'Pallet Racks', 'Shaft Racks'}, sheet names
		Values : sheet ``DataFrame``

	Attributes
	----------
	sheet_col_map : OrderedDict
		Keys : {'Job Bins', 'Pallet Racks', 'Shaft Racks'}, sheet names
		Values : The sheet column name ``str`` that contains part storage 
		locations.

	"""
	def __init__(self, wb):
		self._wb = wb
		self.sheet_col_map = OrderedDict()
		self.sheet_col_map['Job Bins'] = 'Bin Number:'
		self.sheet_col_map['Pallet Racks'] = 'Bin Number:'
		self.sheet_col_map['Shaft Racks'] = 'Location:'

	@property
	def wb(self):
		"""dict : ``DataFrames`` derived from an XLSX document, organized by 
		XLSX sheet name.

		"""
		return self._wb

	@wb.setter
	def wb(self, new_wb):
		self._wb = new_wb

	def _search(self, job_num, sheet, return_col):
		"""Search a ``Dataframe`` for part storage locations.

		Parameters
		----------
		job_num : int
			A 6-digit integer.

		sheet : {'Job Bins', 'Pallet Racks', 'Shaft Racks'}
			The `wb` key that returns the ``Dataframe``.
			
		return_col : {'Bin Number:', Location:'}
			The column name that contains part storage locations.

		Returns
		-------
		list
			Search results, which may contain ``float`` or ``str`` objects, or 
			an error message.

		"""
		try:
			ws = self._wb[sheet]
			results = ws.loc[ws['Job Number:'] == job_num, return_col].tolist()
		except xlrd.biffh.XLRDError:
			return ['Invalid sheet name: %s' % sheet]
		except KeyError:
			return ['Invalid column name: %s' % return_col]
		else:
			if len(results) == 0:
				return ['None']
			else:
				return results

	def search_results(self, job_num):
		"""Get part locations from `wb`.

		Parameters
		----------
		job_num : int
			A 6-digit integer.

		Returns
		-------
		results : dict
			Search result ``lists`` organized by sheet name.

		"""
		results = {}
		for sheet in self.sheet_col_map:
			results[sheet] = self._search(
				job_num, 
				sheet, 
				self.sheet_col_map[sheet]
			)
		return results

	def max_value_len(self, dictionary):
		"""Get the greatest length of a dictionary's values.

		Parameters
		----------
		dictionary : dict
			Must contain iterable values.
		
		Returns
		-------
		max_len : int

		"""
		max_len = 1
		for key in dictionary:
			length = len(dictionary[key])
			if length > max_len:
				max_len = length
		return max_len


class WeekendSignUp(object):
	"""
	Represents a user's weekend availability.

	The user's availability is saved to a filename in the user's folder.

	Parameters
	----------
	user_folder : str
		User folder for the active user.

	Attributes
	----------
	view : WeekendSignUpView

	See Also
	--------
	appdata.UserData

	"""
	def __init__(self, user_folder):
		self._user_folder = user_folder
		self._available = os.path.join(self._user_folder, 'weekend.yes')
		self._unavailable = os.path.join(self._user_folder, 'weekend.no')
		self.view = WeekendSignUpView()
		self.view.yes_btn.clicked.connect(lambda: self._on_click_btn())
		self.view.no_btn.clicked.connect(lambda: self._on_click_btn(False))
		self._set_init_state()

	def _on_click_btn(self, available=True):
		"""Modify view state per button click.

		Parameters
		----------
		available : bool, optional
			The user's weekend availability, determines ``ImageButton`` states.

		"""
		self._update_file(available)
		if available:
			self.view.yes_btn.setEnabled(False)
			self.view.no_btn.setEnabled(True)
		else:
			self.view.yes_btn.setEnabled(True)
			self.view.no_btn.setEnabled(False)

	def _update_file(self, available=True):
		"""Modify a filename in the user's folder.

		Parameters
		----------
		available : bool, optional
			The user's weekend availability, determines how to rename the data 
			file.
		
		"""
		try:
			if available:
				os.rename(self._unavailable, self._available)
			else:
				os.rename(self._available, self._unavailable)
		except OSError:
			# The system cannot find the file, create a new one.
			self._reset(available)

	def _reset(self, available=True):
		"""Create a file in the user's folder.

		Parameters
		----------
		available : bool, optional
			The user's weekend availability, determines the name of the new 
			data file.

		"""
		if available:
			with open(self._available, 'wb') as f:
				pass
		else:
			with open(self._unavailable, 'wb') as f:
				pass

	def _set_init_state(self):
		"""Set view state at startup."""
		if os.path.exists(self._available):
			self.view.yes_btn.setEnabled(False)
		elif os.path.exists(self._unavailable):
			self.view.no_btn.setEnabled(False)
		else:
			# No data file found.
			self._reset()
			self._set_init_state()


class WeekendSignUpView(QtGui.QDockWidget):
	"""
	An dockable interface where users can toggle between two weekend 
	availability states.

	Attributes
	----------
	yes_btn : ImageButton
	no_btn : ImageButton

	"""
	_DOCK_FIXED_HEIGHT = 90
	# _DOCK_MAX_WIDTH = 200
	_BTN_HEIGHT = 35

	def __init__(self):
		# Build GUI
		super(WeekendSignUpView, self).__init__('Weekend Work')
		self.setFixedHeight(self._DOCK_FIXED_HEIGHT)
		# self.setMaximumWidth(self._DOCK_MAX_WIDTH)
		self._widget = QtGui.QWidget()
		self._layout = QtGui.QHBoxLayout(self._widget)
		self._layout.addWidget(QtGui.QLabel('Are you available?'))
		self.yes_btn = ImageButton(Image.AVAILABLE, self._layout)
		self.yes_btn.myheight = self._BTN_HEIGHT
		self.no_btn = ImageButton(Image.UNAVAILABLE, self._layout)
		self.no_btn.myheight = self._BTN_HEIGHT
		self.setWidget(self._widget)


class WeekendRoster(object):
	"""
	Represents a roster of weekend work volunteers.

	Attributes
	----------
	view : WeekendRosterView

	"""
	def __init__(self, users):
		self._users = users
		self.view = WeekendRosterView()
		self.view.table.customContextMenuRequested.connect(self._show_menu)
		self._context = RosterContextMenu(self.view.table)
		self._context.refresh.triggered.connect(self.refresh)
		self.refresh()

	def refresh(self):
		"""Update view."""
		self.view.table.set_table(self._get_attendees())

	def _get_attendees(self):
		"""Returns the ``list`` of employee names that have volunteered to work
		the weekend.

		"""
		attendees = []
		for u in os.listdir(Path.USERS):
			if os.path.exists(os.path.join(Path.USERS, u, 'weekend.yes')):
				name = self._users.get_users_name(u)
				if name is None:
					# The username that corresponds to the existing user folder
					# is no longer registered. This will occur when a user is 
					# removed from the data file. Expired user folders will be 
					# retained for statistical analysis.
					continue
				attendees.append(self._users.get_users_name(u))
		return attendees	

	def _show_menu(self):
		"""Display ``RosterContextMenu`` on screen."""
		self._context.popup(QtGui.QCursor.pos()) 


class WeekendRosterView(QtGui.QDockWidget):
	"""
	A dockable interface that displays the names of weekend work volunteers.

	Attributes
	----------
	table : WeekendRosterTable

	"""
	def __init__(self):
		super(WeekendRosterView, self).__init__('Weekend Roster')
		self.table = WeekendRosterTable()
		self.setWidget(self.table)


class WeekendRosterTable(Table):
	"""
	A ``Table`` that contains the names of weekend work volunteers.

	"""
	def __init__(self):
		super(WeekendRosterTable, self).__init__([])
		self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.setColumnCount(1)
		self.horizontalHeader().hide()

	def set_table(self, attendees):
		"""Set ``Table`` contents.

		Parameters
		----------
		attendees : list
			The names of weekend work volunteers.
		
		"""
		self.setRowCount(0)
		self.setRowCount(len(attendees))
		for i in range(len(attendees)):
			self.setItem(i, 0, TableItem(attendees[i]))


if __name__ == '__main__':
	pass



