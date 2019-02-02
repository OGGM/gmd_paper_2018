# Python imports
import json
import os

# Libs
import numpy as np

# Locals
import oggm
from oggm import cfg, utils, tasks, workflow
from oggm.workflow import execute_entity_task
from oggm.core.massbalance import (ConstantMassBalance, PastMassBalance,
                                   MultipleFlowlineMassBalance)

# Module logger
import logging
log = logging.getLogger(__name__)

# RGI Version
rgi_version = '61'
reset = False

# Initialize OGGM and set up the run parameters
cfg.initialize()

# Local paths (where to write the OGGM run output)
WORKING_DIR = os.path.join(os.path.expanduser('~/tmp'), 'OGGM_GMD',
                           'OGGM_ref_mb_RGIV{}'.format(rgi_version))
cfg.PATHS['working_dir'] = WORKING_DIR
utils.mkdir(WORKING_DIR, reset=reset)
cfg.PARAMS['auto_skip_task'] = True

# We are running the calibration ourselves
cfg.PARAMS['run_mb_calibration'] = True

# We are using which baseline data?
cfg.PARAMS['baseline_climate'] = 'CRU'

# No need for intersects since this has an effect on the inversion only
cfg.PARAMS['use_intersects'] = False

# Use multiprocessing?
cfg.PARAMS['use_multiprocessing'] = True

# Set to True for operational runs
cfg.PARAMS['continue_on_error'] = False

# Get the reference glacier ids (they are different for each RGI version)
rgi_dir = utils.get_rgi_dir(version=rgi_version)
df, _ = utils.get_wgms_files()
rids = df['RGI{}0_ID'.format(rgi_version[0])]

# We can't do Antarctica
rids = [rid for rid in rids if not ('-19.' in rid)]

# Make a new dataframe with those (this takes a while)
log.info('Reading the RGI shapefiles...')
rgidf = utils.get_rgi_glacier_entities(rids, version=rgi_version)
log.info('For RGIV{} we have {} candidate reference '
         'glaciers.'.format(rgi_version, len(rgidf)))

# We have to check which of them actually have enough mb data.
# Let OGGM do it:
gdirs = workflow.init_glacier_regions(rgidf)

# We need to know which period we have data for
log.info('Process the climate data...')
execute_entity_task(tasks.process_cru_data, gdirs, print_log=False)
gdirs = utils.get_ref_mb_glaciers(gdirs)

# Keep only these
rgidf = rgidf.loc[rgidf.RGIId.isin([g.rgi_id for g in gdirs])]

# Save
log.info('For RGIV{} we have {} reference glaciers.'.format(rgi_version,
                                                            len(rgidf)))
rgidf.to_file(os.path.join(WORKING_DIR, 'mb_ref_glaciers.shp'))

# Sort for more efficient parallel computing
rgidf = rgidf.sort_values('Area', ascending=False)

# Go - initialize glacier directories
gdirs = workflow.init_glacier_regions(rgidf)

# Prepro tasks
task_list = [
    tasks.glacier_masks,
    tasks.compute_centerlines,
    tasks.initialize_flowlines,
    tasks.catchment_area,
    tasks.catchment_intersections,
    tasks.catchment_width_geom,
    tasks.catchment_width_correction,
]
for task in task_list:
    execute_entity_task(task, gdirs)

# Climate tasks
if reset:
    tasks.compute_ref_t_stars(gdirs)
execute_entity_task(tasks.local_t_star, gdirs)
execute_entity_task(tasks.mu_star_calibration, gdirs)

# We store the associated params
mb_calib = gdirs[0].read_pickle('climate_info')['mb_calib_params']
with open(os.path.join(WORKING_DIR, 'mb_calib_params.json'), 'w') as fp:
    json.dump(mb_calib, fp)

# And also some statistics
utils.compile_glacier_statistics(gdirs)

# Tests: for all glaciers, the mass-balance around tstar and the
# bias with observation should be approx 0
for gd in gdirs:

    mb_mod = MultipleFlowlineMassBalance(gd,
                                         mb_model_class=ConstantMassBalance,
                                         use_inversion_flowlines=True,
                                         bias=0)  # bias=0 because of calib!
    mb = mb_mod.get_specific_mb()
    np.testing.assert_allclose(mb, 0, atol=5)  # atol for numerical errors

    mb_mod = MultipleFlowlineMassBalance(gd, mb_model_class=PastMassBalance,
                                         use_inversion_flowlines=True)

    refmb = gd.get_ref_mb_data().copy()
    refmb['OGGM'] = mb_mod.get_specific_mb(year=refmb.index)
    np.testing.assert_allclose(refmb.OGGM.mean(), refmb.ANNUAL_BALANCE.mean(),
                               atol=5)  # atol for numerical errors

# Log
log.info('Calibration is done!')
