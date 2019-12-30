#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from os.path import dirname
from os.path import join as osjoin
from os.path import split as ossplit
from sulzer import defaults


__author__ = 'Brandon McCleary'


class Path():
    """
    Contains file and directory paths for ``Nucleus`` application.

    See Also
    --------
    sulzer.defaults
    
    """
    # In either case, get the top-level nucleus directory.
    if ossplit(sys.executable)[1] == 'python.exe':
        # Dev mode
        ROOT = dirname(dirname(__file__))
    else:
        # Production mode
        ROOT = dirname(dirname(dirname(dirname(sys.executable))))

    # Local directories
    DATA = osjoin(ROOT, 'data')
    CORE = osjoin(DATA, 'core')
    IMG = osjoin(DATA, 'images')
    JOBS = osjoin(DATA, 'jobs')
    TEMP = osjoin(DATA, 'temp')
    USERS = osjoin(DATA, 'users')

    # Network directories
    VAULT = defaults.Path.VAULT
    P_FOLDER = defaults.Path.PROJECTS_FOLDER
    REV_ENGR = defaults.Path.REVERSE_ENGINEERING
    PHOTOS = defaults.Path.AX_PICS
    CAD_FORMS = defaults.Path.CAD_FORMS
    QC_MODELS = defaults.Path.QC_MODELS
    DXF_GEN = defaults.Path.DXF_GEN
    DXF_TOOL = defaults.Path.DXF_TOOL
    TEMPLATES = 'Q:\\DRAFT\\Inventor\\Templates\\Nucleus Templates'

    # Local files
    VERSION_DOC = osjoin(ROOT, 'docs', 'Version Control.pdf')
    DATA_XLSX = osjoin(CORE, 'data.xlsx')

    # Network files
    PART_LOC_XLSX = 'L:\\Division2\\PROJECTS FOLDER\\1-Work In Progress ' \
        'STORAGE\\BAL\\Shop Storage.xlsx'


class Image():
    """
    Contains image paths for ``Nucleus`` application.
    
    """
    ROOT = Path.IMG
    LOGO = osjoin(ROOT, 'logo.png')
    SEARCH = osjoin(ROOT, 'search.png')
    VAULT = osjoin(ROOT, 'vault.png')
    P_FOLDER = osjoin(ROOT, 'network.png')
    REV_ENGR = osjoin(ROOT, 'scan.png')
    CAMERA = osjoin(ROOT, 'camera.png')
    EMAIL = osjoin(ROOT, 'email.png')
    AGREEMENT = osjoin(ROOT, 'agreement.png')
    NEW_JOB = osjoin(ROOT, 'new job.png')
    OPEN = osjoin(ROOT, 'open.png')
    SAVE = osjoin(ROOT, 'save.png')
    COMPLETE = osjoin(ROOT, 'completed.png')
    AVAILABLE = osjoin(ROOT, 'available.png')
    UNAVAILABLE = osjoin(ROOT, 'unavailable.png')
    ADD = osjoin(ROOT, 'add.png')
    REFRESH = osjoin(ROOT, 'refresh.png')
    CALENDAR = osjoin(ROOT, 'calendar.png')
    NEW_PROJECT = osjoin(ROOT, 'new project.png')
    COPY = osjoin(ROOT, 'copy.png')
    ALIAS = osjoin(ROOT, 'alias.png')
    DELETE = osjoin(ROOT, 'delete.png')
    NUMBER = osjoin(ROOT, 'number.png') 
    OWNER = osjoin(ROOT, 'owner.png') 
    NOTE = osjoin(ROOT, 'note.png') 
    PRINT = osjoin(ROOT, 'print.png')
    LINK = osjoin(ROOT, 'link.png')
    ZERO = osjoin(ROOT, 'zero.png')
    ACTIVE = osjoin(ROOT, 'active.png')
    UPLOAD = osjoin(ROOT, 'upload.png')
    ABOUT = osjoin(ROOT, 'about.png')
    VERSION = osjoin(ROOT, 'version.png')


if __name__ == '__main__':
    pass


