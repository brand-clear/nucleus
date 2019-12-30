

import sys
import unittest
import xlrd
import os.path
from test import SEARCH_PATH
sys.path.append(SEARCH_PATH)
from part_locator import PartLocatorActions


# Get spreadsheet from test folder
WB = os.path.join(os.path.dirname(__file__), 'shop storage.xlsx')


class TestPartLocatorActions(unittest.TestCase):

    def setUp(self):
        self.parts = PartLocatorActions(WB)

    def test_search_jobbins_returns_1_and_3(self):
        result = self.parts._search(127193, 'Job Bins', 'Bin Number:')
        self.assertEqual([1.0, 3.0], result)

    def test_search_palletrack_returns_b83(self):
        result = self.parts._search(130078, 'Pallet Racks', 'Bin Number:')
        self.assertEqual(['B83'], result)

    def test_search_jobbins_returns_nonestringlist(self):
        result = self.parts._search(000000, 'Job Bins', 'Bin Number:')
        self.assertEqual(['None'], result) 

    def test_search_shaftrack_returns_rack2(self):
        result = self.parts._search(127947, 'Shaft Racks', 'Location:')
        self.assertEqual(['Rack 2'], result)

    def test_search_returns_collective_results(self):
        result = self.parts._search(999998, 'Job Bins', 'Bin Number:')
        self.assertEqual(['None'], result)
        result = self.parts._search(999998, 'Pallet Racks', 'Bin Number:')
        self.assertEqual(['A43'], result)
        result = self.parts._search(999998, 'Shaft Racks', 'Location:')
        self.assertEqual(['Rack 2', 'Rack 2', 'Rack 2'], result)

    def test_search_raised_xlrderror(self):
        result = self.parts._search(127947, 'test', 'Location:')
        self.assertEqual(['Invalid sheet name: test'], result)

    def test_search_raised_keyerror(self):
        result = self.parts._search(127947, 'Shaft Racks', 'test')
        self.assertEqual(['Invalid column name: test'], result)

    def test_search_raised_ioerror(self):
        self.parts._wb = 'test'
        result = self.parts._search(127947, 'Shaft Racks', 'test')
        self.assertEqual(['Unable to locate spreadsheet'], result)

    def test_max_value_len_returns_3(self):
        d = {'a':[1,20], 'b':[2,2,2], 'c':['None']}
        self.assertEqual(3, self.parts.max_value_len(d))


if __name__ == '__main__':
    try:
        unittest.main(verbosity=2)
    except SystemExit:
        pass