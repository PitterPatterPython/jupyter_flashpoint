#! /usr/bin/env python3

"""prep_local_dev.py: from ipython, %run prep_local_dev.py to import the dependencies needed
        to test dev changes to this repo.
"""

__author__ = "Rob D'Aveta"
__credits__ = ["Rob D'Aveta"]
__version__ = "0.0.1"
__maintainer__ = "Rob D'Aveta"
__email__ = "rob.daveta@gmail.com"

import sys

# You will need to clone the jupyter_integration_base repository to your local
# environment, and append its path below - https://github.com/JohnOmernik/jupyter_integration_base
sys.path.append('../jupyter_integration_base')

ipy = get_ipython()
from integration_core.integration_base import Integration
from flashpoint_core.flashpoint_base import Flashpoint
flashpoint_base = Flashpoint(ipy, debug=False)
ipy.register_magics(flashpoint_base)
