import os
import sys
import cPickle as pickle
from datetime import datetime, timedelta
from PyQt4 import QtGui, QtCore
from pyqtauto import setters
from pyqtauto.widgets import Spacer, Table, TableItem, Workspace, ImageButton
from core import Image, Path
from work_orders import WorkOrderConstants


__author__ = 'Brandon McCleary'


class Note(QtGui.QGroupBox):
    """
    Represents a singular graphical note.

    Parameters
    ----------
    header : str
    body : str

    """
    def __init__(self, header, body):
        super(Note, self).__init__()
        self.setTitle(header)
        self._layout = QtGui.QVBoxLayout(self)
        self._body = QtGui.QLabel(body)
        self._body.wordWrap()
        self._layout.addWidget(self._body)
        self._layout.addItem(Spacer())


class NoteBox(QtGui.QScrollArea):
    """
    Represents a scrollable platform which hosts a collection of graphical notes.

    """
    def __init__(self):
        super(NoteBox, self).__init__()
        self.setWidgetResizable(True)
        self._widget = QtGui.QWidget()
        self._layout = QtGui.QVBoxLayout(self._widget)
        self._layout.setSpacing(10)
        self.setWidget(self._widget)

    def clear(self):
        """Remove all existing notes from NoteBox."""
        for i in range(self._layout.count()):
            try:
                self._layout.itemAt(i).widget().setParent(None)
            except AttributeError:
                pass

    def add(self, header, body):
        """
        Parameters
        ----------
        header : str
        body : str

        """
        self._layout.insertWidget(0, Note(header, body))

    def set_notes(self, note_dict):
        """
        Parameters
        ----------
        note_dict : NoteDict

        """
        self.clear()
        for key in note_dict.keys():
            self.add(key, note_dict[key])


class ProjectTable(Table):
    """
    Represents a ``Table`` that contains information about active CAD department 
    projects.

    Attributes
    ----------
    owner_options : list
    alias_num_options : list
    dwg_num_options : list
    due_date_options : list
    status_options : list
 
    """
    HEADERS = [
        'Alias',
        'Drawing No.',
        'Owner',
        'Due Date',
        'Status'
    ]

    def __init__(self):
        super(ProjectTable, self).__init__(self.HEADERS)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setSortingEnabled(True)

    def set_table(self, projects):
        """Set ``Table`` contents.

        Parameters
        ----------
        projects : dict
            ``Projects`` organized by drawing or alias number.

        Notes
        -----
        setSortingEnabled is disabled, then enabled to combat a PyQt bug. Do not
        remove this functionality from this method.

        """
        self.setSortingEnabled(False)
        self.setRowCount(0)
        keys = projects.keys()
        row_count = len(keys)
        self.setRowCount(row_count)
        for i in range(row_count):
            self.set_row(i, keys[i], projects[keys[i]])
        self.setSortingEnabled(True)

    def set_row(self, row, dwg_num, project):
        """Set a ``Table`` row.

        Parameters
        ----------
        row : int
            ``Table`` row index.

        dwg_num : str
            A drawing or alias number.

        project : Project

        """
        self.setItem(row, 0, TableItem(project.alias_num))
        self.setItem(row, 1, TableItem(dwg_num))
        self.setItem(row, 2, TableItem(project.owner))
        self.setItem(row, 3, TableItem(project.due_date))
        self.setItem(row, 4, TableItem(project.status))

    @property
    def selected_dwg_nums(self):
        """list: The drawing numbers associated with selected ``Table`` rows."""
        dwg_nums = []
        indices = self.selectionModel().selectedRows()
        for i in indices:
            dwg_nums.append(
                str(
                    self.item(i.row(), 
                    self.HEADERS.index('Drawing No.')).text()
                )
            )
        return dwg_nums

    @property
    def existing_alias_nums(self):
        """set: The alias numbers found in ``Table``."""
        return self.column_set(self.HEADERS.index('Alias'))

    @property
    def existing_dwg_nums(self):
        """set: The drawing numbers found in ``Table``."""
        return self.column_set(self.HEADERS.index('Drawing No.'))

    @property
    def alias_num_options(self):
        """list: The alias numbers found in ``Table``, plus 'New'. """
        options = list(self.existing_alias_nums)
        options.append('New')
        return options

    @property
    def due_date_options(self):
        """list: Future due dates based on today's date, plus 'Custom'."""
        today = datetime.now()
        format = WorkOrderConstants.DATE_FORMAT
        dates = [
            (today + timedelta(days=1)).strftime(format),
            (today + timedelta(days=2)).strftime(format),
            (today + timedelta(days=7)).strftime(format),
            (today + timedelta(days=30)).strftime(format),
            'New'
        ]
        return dates

    @property
    def status_options(self):
        """list: Per WorkOrderConstants.STATUS_LIST."""
        return WorkOrderConstants.STATUS_LIST

    def column_set(self, col):
        """Get the set of values from a ``Table`` column index.

        Parameters
        ----------
        col : int

        Returns
        -------
        values : set(str)

        """
        values = set()
        for i in range(self.rowCount()):
            values.add(str(self.item(i, col).text()))
        return values


if __name__ == '__main__':
    pass
