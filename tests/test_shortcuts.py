

import sys
import unittest
import os.path
import pandas as pd
from test import SEARCH_PATH
sys.path.append(SEARCH_PATH)
from shortcuts import ShortcutsActions


# Get fake user data from test folder
user_file = os.path.join(os.path.dirname(__file__), 'users.xlsx')
USERS = pd.read_excel(user_file, 'Users')


class TestShortcutsActions(unittest.TestCase):

    # The critical processing items tested below include: confirming the correct 
    # filepaths were saved, confirming the correct user data was retrieved for 
    # emails, and confirming that outlook does not raise an error.

    def setUp(self):
        self.shortcuts = ShortcutsActions(
            '124025', 
            'C:\\Vault WorkSpace\\Draft', 
            USERS
        )

    def test_projectsfolder_is_job(self):
        # Confirm the projects folder for this job was saved
        self.assertEqual(
            self.shortcuts._shortcuts['projects folder'], 
            'L:\\Division2\\PROJECTS FOLDER\\124000-124499\\124025'
        )

    def test_projectsfolder_is_root(self):
        # Confirm the projects folder root was saved since the job number
        # does not exist.
        self.shortcuts = ShortcutsActions('9999999', 'C:\\Vault WorkSpace', USERS)
        self.assertEqual(
            self.shortcuts._shortcuts['projects folder'], 
            'L:\\Division2\\PROJECTS FOLDER'
        )

    def test_revengr_is_job(self):
        # Confirm the reverse engineering folder for this job was saved
        self.assertEqual(
            self.shortcuts._shortcuts['reverse engineering'], 
            'Q:\\DRAFT\\_REVERSE ENGINEERING\\124025'
        )

    def test_revengr_is_root(self):
        # Confirm the reverse engineering folder root was saved since the job 
        # number does not exist.
        self.shortcuts = ShortcutsActions('9999999', 'C:\\Vault WorkSpace', USERS)
        self.assertEqual(
            self.shortcuts._shortcuts['reverse engineering'], 
            'Q:\\DRAFT\\_REVERSE ENGINEERING'
        )

    def test_workspace_is_root(self):
        # Confirm the vault workspace root is saved when an invalid path is
        # passed.
        self.shortcuts = ShortcutsActions('9999999', 'C:\\Vault\\fake', USERS)
        self.assertEqual(
            self.shortcuts._shortcuts['vault workspace'], 
            'C:\\Vault Workspace'
        )

    def test_workspace_is_draft(self):
        # Confirm the vault workspace folder for this job was saved
        self.assertEqual(
            self.shortcuts._shortcuts['vault workspace'], 
            self.shortcuts.workspace
        )

    def test_photos_is_job(self):
        # Confirm the photos folder for this job was saved
        self.assertEqual(
            self.shortcuts._shortcuts['photos'], 
            'T:\\pictures\\Axapta\\124000-199\\124025'
        )  

    def test_photos_is_root(self):
        # Confirm the photos root is saved since the job number does not exist.
        self.shortcuts = ShortcutsActions('9999999', 'C:\\Vault\\fake', USERS)
        self.assertEqual(
            self.shortcuts._shortcuts['photos'], 
            'T:\\pictures\\Axapta'
        )  

    def test_probe_email_addresses_returns_to_field(self):
        # Confirm that correct email addresses were returned
        actual_to = ['to_1@sulzer.com', 'to_2@sulzer.com']
        self.assertEqual(self.shortcuts._to, actual_to)

    def test_probe_email_addresses_returns_cc_field(self):
        # Confirm that correct email addresses were returned
        actual_cc = ['cc_1@sulzer.com', 'cc_2@sulzer.com']
        self.assertEqual(self.shortcuts._cc, actual_cc)

    @unittest.skip('for visual checking only')
    def test_send_probe_email_does_not_return_error(self):
        # This is validated if a new outlook email pops up
        # All other email tests are visually validated here also
        self.shortcuts.send_probe_email()

    @unittest.skip('for visual checking only')
    def test_open_agreement_visually(self):
        # Validate GUI appearance
        try:
            from PyQt4 import QtGui
            app = QtGui.QApplication(sys.argv)
            self.shortcuts.open_agreement()
            sys.exit(app.exec_())
        except SystemExit:
            # Triggered when closing app
            pass


if __name__ == '__main__':
    try:
        unittest.main(verbosity=2)
    except SystemExit:
        pass
