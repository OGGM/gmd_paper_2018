import os
import time
import logging
import geopandas as gpd

# Locals
import oggm.cfg as cfg
from oggm import utils, workflow, tasks

# Time
start = time.time()

# Run settings
rgi_version = '61'
rgi_reg = '{:02}'.format(int(os.environ.get('RGI_REG')))

# Initialize OGGM and set up the run parameters
cfg.initialize(logging_level='WORKFLOW')

# Local paths (where to write output and where to download input)
WORKING_DIR = os.environ["WORKDIR"]
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

# Get the RGI file
rgidf = gpd.read_file(utils.get_rgi_region_file(rgi_reg, version=rgi_version))

# Sort for more efficient parallel computing
rgidf = rgidf.sort_values('Area', ascending=False)

# Module logger
log = logging.getLogger(__name__)
log.info('Starting run for RGI reg: ' + rgi_reg)
log.info('Number of glaciers: {}'.format(len(rgidf)))

# Go - initialize working directories
gdirs = workflow.init_glacier_regions(rgidf, from_prepro_level=3)

# Tasks
task_list = [
    tasks.compute_centerlines,
    tasks.initialize_flowlines,
    tasks.compute_downstream_line,
    tasks.compute_downstream_bedshape,
    tasks.catchment_area,
    tasks.catchment_intersections,
    tasks.catchment_width_geom,
    tasks.catchment_width_correction,
    tasks.local_t_star,
    tasks.mu_star_calibration,
    tasks.prepare_for_inversion,
    tasks.mass_conservation_inversion,
    tasks.filter_inversion_output,
]
for task in task_list:
    workflow.execute_entity_task(task, gdirs)

# Glacier stats
utils.compile_glacier_statistics(gdirs,
                                 filesuffix='_{}'.format(rgi_reg))
utils.compile_climate_statistics(gdirs, add_climate_period=[1920, 1960, 2000],
                                 filesuffix='_{}'.format(rgi_reg))

# End - compress all
workflow.execute_entity_task(utils.gdir_to_tar, gdirs)

# Log
m, s = divmod(time.time() - start, 60)
h, m = divmod(m, 60)
log.info("OGGM is done! Time needed: %02d:%02d:%02d" % (h, m, s))
