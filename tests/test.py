

from os.path import dirname
from os.path import join as osj


# Add this to sys.path at the beginning of all test modules
SEARCH_PATH = osj(dirname(dirname(__file__)), 'nucleus')
