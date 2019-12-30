

import sys
import unittest
from datetime import datetime
from test import SEARCH_PATH
sys.path.append(SEARCH_PATH)
from work_orders import NoteDict, Job


class TestNoteDict(unittest.TestCase):

    def setUp(self):
        self.notes = NoteDict('this is a test')

    def test_init_header(self):
        self.assertEqual(['Work Instructions'], self.notes.keys())

    def test_init_note(self):
        self.assertEqual('this is a test', self.notes['Work Instructions'])

    def test_new_note(self):
        self.notes.add('new note', 'Brandon')
        self.assertEqual('new note', self.notes[self.notes.keys()[1]])


class TestJob(unittest.TestCase):

    def setUp(self):
        self.job = Job('105000')

    def test_add_project(self):
        alias = '105000.177-43'
        self.job.add_project(
            alias,
            'these are work instructions',
            'Brandon',
            '1/1/2020'
        )
        self.assertEqual(self.job.projects.keys(), [alias])
        self.assertEqual(self.job.projects[alias].status, 'Unassigned')

    def test_del_project(self):
        alias = '105000.177-43'
        self.job.add_project(
            alias,
            'these are work instructions',
            'Brandon',
            '1/1/2020'
        )
        self.job.del_project(alias)
        with self.assertRaises(KeyError):
            self.job.del_project(alias)
    

if __name__ == '__main__':
    try:
        unittest.main(verbosity=2)
    except SystemExit:
        pass
