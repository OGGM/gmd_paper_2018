# This will run OGGM pre-processing on the RGI region of your choice
from __future__ import division
import oggm

# Module logger
import logging
log = logging.getLogger(__name__)

# Python imports
import os
import sys
from glob import glob
import shutil
from functools import partial
# Libs
import pandas as pd
import geopandas as gpd
import numpy as np
import shapely.geometry as shpg
import matplotlib.pyplot as plt
# Locals
import oggm
import oggm.cfg as cfg
from oggm import workflow
from oggm.utils import get_demo_file
from oggm import tasks
from oggm.workflow import execute_entity_task, reset_multiprocessing
from oggm import graphics, utils
# Time
import time
start = time.time()

# Regions:
# Alaska 01
# Western Canada and US 02
# Arctic Canada North 03
# Arctic Canada South 04
# Greenland 05
# Iceland 06
# Svalbard 07
# Scandinavia 08
# Russian Arctic 09
# North Asia 10
# North Asia 10
# Central Europe 11
# Caucasus and Middle East 12
# Central Asia 13
# South Asia West 14
# South Asia East 15
# Low Latitudes 16
# Southern Andes 17
# New Zealand 18
# Antarctic and Subantarctic 19
rgi_reg = '{:02}'.format(int(os.environ.get('RGI_REG')))

rgi_version = '6'


# Initialize OGGM and set up the run parameters
# ---------------------------------------------

cfg.initialize()

SLURM_WORKDIR = os.environ["WORKDIR"]

# Local paths (where to write output and where to download input)
WORKING_DIR = SLURM_WORKDIR
utils.mkdir(WORKING_DIR)
cfg.PATHS['working_dir'] = WORKING_DIR

# Use multiprocessing?
cfg.PARAMS['use_multiprocessing'] = True

# How many grid points around the glacier?
# Make it large if you expect your glaciers to grow large
cfg.PARAMS['border'] = 160

# Set to True for operational runs
cfg.PARAMS['continue_on_error'] = True
cfg.PARAMS['auto_skip_task'] = False

# But we use intersects
rgi_dir = utils.get_rgi_intersects_dir(version=rgi_version)
rgi_shp = list(glob(os.path.join(rgi_dir, "*", '*intersects*' + rgi_reg + '_rgi' + rgi_version + '0_*.shp')))
assert len(rgi_shp) == 1
cfg.set_intersects_db(rgi_shp[0])

# Pre-download other files which will be needed later
_ = utils.get_cru_file(var='tmp')
_ = utils.get_cru_file(var='pre')


# Copy the RGI file
# -----------------

# Download RGI files
rgi_dir = utils.get_rgi_dir(version=rgi_version)
rgi_shp = list(glob(os.path.join(rgi_dir, "*", rgi_reg+ '_rgi' + rgi_version + '0_*.shp')))
assert len(rgi_shp) == 1
rgidf = gpd.read_file(rgi_shp[0])

# Sort for more efficient parallel computing
rgidf = rgidf.sort_values('Area', ascending=False)

log.info('Starting run for RGI reg: ' + rgi_reg)
log.info('Number of glaciers: {}'.format(len(rgidf)))

# Go - initialize working directories
# -----------------------------------
gdirs = workflow.init_glacier_regions(rgidf)

# Prepro tasks
task_list = [
    tasks.glacier_masks,
    tasks.compute_centerlines,
    tasks.initialize_flowlines,
    tasks.compute_downstream_line,
    tasks.compute_downstream_bedshape,
    tasks.catchment_area,
    tasks.catchment_intersections,
    tasks.catchment_width_geom,
    tasks.catchment_width_correction,
]
for task in task_list:
    execute_entity_task(task, gdirs)

# Climate tasks -- only data preparation and tstar interpolation!
execute_entity_task(tasks.process_cru_data, gdirs)
tasks.distribute_t_stars(gdirs)
execute_entity_task(tasks.apparent_mb, gdirs)

# Inversion tasks
execute_entity_task(tasks.prepare_for_inversion, gdirs)
execute_entity_task(tasks.volume_inversion, gdirs, glen_a=cfg.A, fs=0)
execute_entity_task(tasks.filter_inversion_output, gdirs)
execute_entity_task(tasks.init_present_time_glacier, gdirs)

# Compile output
utils.glacier_characteristics(gdirs)

# Log
m, s = divmod(time.time() - start, 60)
h, m = divmod(m, 60)
log.info("OGGM is done! Time needed: %02d:%02d:%02d" % (h, m, s))

