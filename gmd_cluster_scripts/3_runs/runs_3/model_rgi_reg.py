# This will run OGGM on the RGI region of your choice
# After preprocessing, the glaciers are run for 1000 years in a random climate
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
cfg.PARAMS['continue_on_error'] = True
SLURM_WORKDIR = os.environ["WORKDIR"]
INPUTDIR = '/home/users/fmaussion/run_output/rgi_reg_' + rgi_reg
utils.mkdir(SLURM_WORKDIR)

# Download RGI files
log.info('Download RGI files...')
rgi_dir = utils.get_rgi_dir(version=rgi_version)
rgi_shp = list(glob(os.path.join(rgi_dir, "*", rgi_reg+ '_rgi' + rgi_version + '0_*.shp')))
assert len(rgi_shp) == 1
rgidf = gpd.read_file(rgi_shp[0])

# Sort for more efficient parallel computing
rgidf = rgidf.sort_values('Area', ascending=False)

# Then we have to copy the directories
log.info('Copy the glacier directories for run...')
cfg.PATHS['working_dir'] = INPUTDIR
gdirs = workflow.init_glacier_regions(rgidf)
new_base = os.path.join(SLURM_WORKDIR, 'per_glacier')
for gdir in gdirs:
    gdir.copy_to_basedir(new_base, setup='inversion')

# Copy the log task to append to it
shutil.copyfile(os.path.join(INPUTDIR, 'task_log.csv'), 
                os.path.join(SLURM_WORKDIR, 'task_log.csv'))

# Back to normal
reset_multiprocessing()
cfg.initialize()

cfg.PATHS['working_dir'] = SLURM_WORKDIR

# Use multiprocessing?
cfg.PARAMS['use_multiprocessing'] = True

# Set to True for operational runs
cfg.PARAMS['continue_on_error'] = True
cfg.PARAMS['auto_skip_task'] = False

log.info('Starting run for RGI reg: ' + rgi_reg)
log.info('Number of glaciers: {}'.format(len(rgidf)))

# Go - initialize working directories
# -----------------------------------
gdirs = workflow.init_glacier_regions(rgidf)

# Inversion tasks
execute_entity_task(tasks.prepare_for_inversion, gdirs, invert_all_rectangular=True)
execute_entity_task(tasks.volume_inversion, gdirs, glen_a=cfg.A, fs=0)
execute_entity_task(tasks.filter_inversion_output, gdirs)
execute_entity_task(tasks.init_present_time_glacier, gdirs)

# Runs
nyears = 300
task_names = []

fsuf = '_rect_rdn_tstar'
log.info('Start experiment ' + fsuf)
execute_entity_task(tasks.random_glacier_evolution, gdirs,
                    nyears=nyears, bias=0,
                    filesuffix=fsuf)
log.info('Compiling output ' + fsuf + ' ...')
utils.compile_run_output(gdirs, filesuffix=fsuf)
task_names.append('random_glacier_evolution' + fsuf)

fsuf = '_rect_ct_tstar'
log.info('Start experiment ' + fsuf)
execute_entity_task(tasks.run_constant_climate, gdirs,
                    nyears=nyears, bias=0,
                    filesuffix=fsuf)
log.info('Compiling output ' + fsuf + ' ...')
utils.compile_run_output(gdirs, filesuffix=fsuf)
task_names.append('run_constant_climate' + fsuf)

utils.compile_task_log(gdirs, task_names=task_names)

# Log
m, s = divmod(time.time() - start, 60)
h, m = divmod(m, 60)
log.info("OGGM is done! Time needed: %02d:%02d:%02d" % (h, m, s))
