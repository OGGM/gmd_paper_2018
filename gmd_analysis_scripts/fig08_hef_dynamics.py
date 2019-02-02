import os

import matplotlib.pyplot as plt
import xarray as xr
import numpy as np

import oggm
from oggm import cfg, tasks
from oggm import utils
from gmd_analysis_scripts import PLOT_DIR
from oggm.utils import get_rgi_glacier_entities, get_rgi_intersects_entities, mkdir

fig_path = os.path.join(PLOT_DIR, 'hef_dyns.pdf')

cfg.initialize()

# Don't use intersects
cfg.set_intersects_db()
cfg.PARAMS['border'] = 320

base_dir = os.path.join(os.path.expanduser('~/tmp'), 'OGGM_GMD', 'dynamics')
cfg.PATHS['working_dir'] = base_dir
mkdir(base_dir, reset=True)

entity = get_rgi_glacier_entities(['RGI60-11.00897']).iloc[0]
gdir = oggm.GlacierDirectory(entity, base_dir=base_dir)
cfg.set_intersects_db(get_rgi_intersects_entities(['RGI60-11.00897']))

tasks.define_glacier_region(gdir, entity=entity)
tasks.glacier_masks(gdir)
tasks.compute_centerlines(gdir)
tasks.initialize_flowlines(gdir)
tasks.compute_downstream_line(gdir)
tasks.compute_downstream_bedshape(gdir)
tasks.catchment_area(gdir)
tasks.catchment_intersections(gdir)
tasks.catchment_width_geom(gdir)
tasks.catchment_width_correction(gdir)
tasks.process_cru_data(gdir)
tasks.local_t_star(gdir)
tasks.mu_star_calibration(gdir)
tasks.prepare_for_inversion(gdir)
tasks.mass_conservation_inversion(gdir)
tasks.filter_inversion_output(gdir)
tasks.init_present_time_glacier(gdir)

df = utils.compile_glacier_statistics([gdir], path=False)

reset = False
seed = 0
glen_a = cfg.PARAMS['glen_a']
fs = 5.7e-20
nyears = 800

tasks.run_random_climate(gdir, nyears=nyears, bias=0, seed=seed,
                         output_filesuffix='_fromzero_def', reset=reset,
                         zero_initial_glacier=True)

tasks.run_constant_climate(gdir, nyears=nyears, bias=0,
                           output_filesuffix='_fromzero_ct', reset=reset,
                           zero_initial_glacier=True)

cfg.PARAMS['fs'] = fs * 0.5
tasks.run_random_climate(gdir, nyears=nyears, bias=0, seed=seed,
                         output_filesuffix='_fromzero_fs', reset=reset,
                         zero_initial_glacier=True)

cfg.PARAMS['fs'] = 0
cfg.PARAMS['glen_a'] = glen_a*2
tasks.run_random_climate(gdir, nyears=nyears, bias=0, seed=seed,
                         output_filesuffix='_fromzero_2A', reset=reset,
                         zero_initial_glacier=True)

cfg.PARAMS['fs'] = 0
cfg.PARAMS['glen_a'] = glen_a/2
tasks.run_random_climate(gdir, nyears=nyears, bias=0, seed=seed,
                         output_filesuffix='_fromzero_halfA', reset=reset,
                         zero_initial_glacier=True)

cfg.PARAMS['fs'] = fs * 0.
cfg.PARAMS['glen_a'] = glen_a
cfg.PARAMS['use_shape_factor_for_fluxbasedmodel'] = "Adhikari"
tasks.run_random_climate(gdir, nyears=nyears, bias=0, seed=seed,
                         output_filesuffix='_fromzero_drag', reset=reset,
                         zero_initial_glacier=True)


f = gdir.get_filepath('model_diagnostics', filesuffix='_fromzero_def')
ds1 = xr.open_dataset(f)
f = gdir.get_filepath('model_diagnostics', filesuffix='_fromzero_fs')
ds2 = xr.open_dataset(f)
f = gdir.get_filepath('model_diagnostics', filesuffix='_fromzero_2A')
ds3 = xr.open_dataset(f)
f = gdir.get_filepath('model_diagnostics', filesuffix='_fromzero_halfA')
ds4 = xr.open_dataset(f)
f = gdir.get_filepath('model_diagnostics', filesuffix='_fromzero_ct')
ds5 = xr.open_dataset(f)
f = gdir.get_filepath('model_diagnostics', filesuffix='_fromzero_drag')
ds6 = xr.open_dataset(f)

letkm = dict(color='black', ha='left', va='top', fontsize=12,
             bbox=dict(facecolor='white', edgecolor='black'))
tx, ty = 0.02, .977
cs = plt.get_cmap('Purples')(np.linspace(0.5, 1, 4))[::-1]
alpha=0.8

f = 0.8
f, (ax1, ax2) = plt.subplots(1, 2, figsize=(9*f, 4*f))

ax = ax1
ax.axhline(df.inv_volume_km3.values[0], 0, 800, color='k', linewidth=0.8)
(ds6.volume_m3 * 1e-9).plot(ax=ax, label='Lateral drag', color=cs[0], alpha=alpha)
(ds4.volume_m3 * 1e-9).plot(ax=ax, label=r'A / 2', color=cs[1], alpha=alpha)
(ds1.volume_m3 * 1e-9).plot(ax=ax, label='Default', color=cs[2], alpha=alpha)
(ds2.volume_m3 * 1e-9).plot(ax=ax, label='Sliding', color=cs[3], alpha=alpha)
ax.set_xlabel('Years')
ax.set_ylabel('Volume [km$^3$]')
ax.text(tx, ty, 'a', transform=ax.transAxes, **letkm)

ax = ax2
ax.axhline(gdir.read_pickle('model_flowlines')[-1].length_m / 1000, 0, 800,
           color='k', linewidth=0.8)
(ds6.length_m / 1000).plot(ax=ax, label='Lateral drag', color=cs[0], alpha=alpha)
(ds4.length_m / 1000).plot(ax=ax, label=r'A / 2', color=cs[1], alpha=alpha)
(ds1.length_m / 1000).plot(ax=ax, label='Default', color=cs[2], alpha=alpha)
(ds2.length_m / 1000).plot(ax=ax, label='Sliding', color=cs[3], alpha=alpha)
ax.set_xlabel('Years')
ax.set_ylabel('Length [km]')
ax.text(tx, ty, 'b', transform=ax.transAxes, **letkm)
plt.legend()

plt.tight_layout()
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
