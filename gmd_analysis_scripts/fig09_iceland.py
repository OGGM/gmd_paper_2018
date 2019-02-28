import os
import geopandas as gpd
import numpy as np
import oggm
import zipfile
from oggm import cfg, tasks, graphics
from oggm.utils import get_rgi_glacier_entities, get_rgi_intersects_entities
import matplotlib.pyplot as plt
import xarray as xr
from oggm import workflow
from oggm.workflow import execute_entity_task
import salem
from oggm import utils
from gmd_analysis_scripts import PLOT_DIR

fig_path = os.path.join(PLOT_DIR, 'iceland.pdf')

cfg.initialize()

cfg.PARAMS['border'] = 60
cfg.PARAMS['auto_skip_task'] = True

base_dir = os.path.join(os.path.expanduser('~/tmp'), 'OGGM_GMD', 'iceland')
utils.mkdir(base_dir, reset=True)
cfg.PATHS['working_dir'] = base_dir

rids = ['RGI60-06.003{}'.format(i) for i in range(13, 27)]

rgidf = get_rgi_glacier_entities(rids)

# Pre-download other files which will be needed later
_ = utils.get_cru_file(var='tmp')
_ = utils.get_cru_file(var='pre')

# Sort for more efficient parallel computing
rgidf = rgidf.sort_values('Area', ascending=False)

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

# Climate tasks
execute_entity_task(tasks.process_cru_data, gdirs)
execute_entity_task(tasks.local_t_star, gdirs)
execute_entity_task(tasks.mu_star_calibration, gdirs)

# Inversion tasks
execute_entity_task(tasks.prepare_for_inversion, gdirs)
execute_entity_task(tasks.mass_conservation_inversion, gdirs)
execute_entity_task(tasks.filter_inversion_output, gdirs)
execute_entity_task(tasks.init_present_time_glacier, gdirs)

# Compile output
# utils.glacier_characteristics(gdirs)
# seed = 0
# execute_entity_task(tasks.random_glacier_evolution, gdirs,
#                     nyears=500, bias=0, seed=seed, temperature_bias=0,
#                     filesuffix='_defaults')
# execute_entity_task(tasks.random_glacier_evolution, gdirs,
#                     nyears=500, bias=0, seed=seed, temperature_bias=-0.2,
#                     filesuffix='_tbias')
#
# utils.compile_run_output(gdirs, filesuffix='_defaults')
# utils.compile_run_output(gdirs, filesuffix='_tbias')
# ds = xr.open_dataset(os.path.join(base_dir, 'run_output_defaults.nc'))
# (ds.volume.sum(dim='rgi_id') * 1e-9).plot()
# plt.show()
# exit()

# We prepare for the plot, which needs our own map to proceed.
# Lets do a local mercator grid
g = salem.mercator_grid(center_ll=(-19.61, 63.63),
                        extent=(18000, 14500))
# And a map accordingly
sm = salem.Map(g, countries=False)
sm.set_lonlat_contours(interval=0)
z = sm.set_topography(os.path.join(cfg.PATHS['tmp_dir'], 'ISL.tif'))
sm.set_data(z)

# Figs
f = 0.75
f, axs = plt.subplots(2, 1, figsize=(7 * f, 10 * f))

graphics.plot_domain(gdirs, ax=axs[0], smap=sm)

letkm = dict(color='black', ha='left', va='bottom', fontsize=16,
             bbox=dict(facecolor='white', edgecolor='black'))
xt, yt = 6, 6
axs[0].text(xt, yt, 'a', **letkm)

sm.set_data()
sm.set_lonlat_contours(interval=0)
sm.set_geometry()
sm.set_text()
graphics.plot_inversion(gdirs, ax=axs[1], smap=sm,
                        linewidth=1, add_scalebar=False,
                        title='', vmax=250)
xt, yt = 6, 6
axs[1].text(xt, yt, 'b', **letkm)
plt.tight_layout()
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
