"""Runtime hook: tell pyproj where its PROJ data lives inside the frozen bundle."""

import os
import sys

if getattr(sys, 'frozen', False):
    proj_data = os.path.join(sys._MEIPASS, 'proj')
    os.environ.setdefault('PROJ_DATA', proj_data)
    os.environ.setdefault('PROJ_LIB', proj_data)
