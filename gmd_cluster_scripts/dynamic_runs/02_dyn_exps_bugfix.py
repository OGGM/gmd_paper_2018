import os
import time
import logging
import geopandas as gpd

# Locals
import salem
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
gdirs = workflow.init_glacier_regions(rgidf, from_prepro_level=4)

# Init glaciers
workflow.execute_entity_task(tasks.init_present_time_glacier, gdirs)

# Runs
nyears = 300
task_names = []

fsuf = '_rdn_2000'
log.info('Start experiment ' + fsuf)
workflow.execute_entity_task(tasks.run_random_climate, gdirs, seed=1,
                             nyears=nyears, y0=2000,
                             output_filesuffix=fsuf)
log.info('Compiling output ' + fsuf + ' ...')
utils.compile_run_output(gdirs, filesuffix=fsuf)
task_names.append('run_random_climate' + fsuf)

fsuf = '_rdn_2000_tbias_p05'
log.info('Start experiment ' + fsuf)
workflow.execute_entity_task(tasks.run_random_climate, gdirs, seed=2,
                             nyears=nyears, y0=2000,
                             temperature_bias=0.5,
                             output_filesuffix=fsuf)
log.info('Compiling output ' + fsuf + ' ...')
utils.compile_run_output(gdirs, filesuffix=fsuf)
task_names.append('run_random_climate' + fsuf)

fsuf = '_rdn_2000_tbias_m05'
log.info('Start experiment ' + fsuf)
workflow.execute_entity_task(tasks.run_random_climate, gdirs, seed=3,
                             nyears=nyears, y0=2000,
                             temperature_bias=-0.5,
                             output_filesuffix=fsuf)
log.info('Compiling output ' + fsuf + ' ...')
utils.compile_run_output(gdirs, filesuffix=fsuf)
task_names.append('run_random_climate' + fsuf)


# End
utils.compile_task_log(gdirs, filesuffix='_2000bf', task_names=task_names)

# Log
m, s = divmod(time.time() - start, 60)
h, m = divmod(m, 60)
log.info("OGGM is done! Time needed: %02d:%02d:%02d" % (h, m, s))
