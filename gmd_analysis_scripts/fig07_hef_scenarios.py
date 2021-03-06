import os
import matplotlib.pyplot as plt
import xarray as xr

import oggm
from oggm import cfg, tasks, graphics
from oggm import utils
from oggm.core.flowline import (FileModel)
from gmd_analysis_scripts import PLOT_DIR
from oggm.utils import get_rgi_glacier_entities, get_rgi_intersects_entities, mkdir

fig_path = os.path.join(PLOT_DIR, 'hef_scenarios.pdf')

cfg.initialize()

cfg.PARAMS['border'] = 60

base_dir = os.path.join(os.path.expanduser('~/tmp'), 'OGGM_GMD', 'scenarios')
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

tasks.run_random_climate(gdir, nyears=800, seed=0, y0=2000,
                         output_filesuffix='_2000_def', reset=reset)

tasks.run_random_climate(gdir, nyears=800, seed=0, y0=1920,
                         output_filesuffix='_1920_def', reset=reset)


f = gdir.get_filepath('model_diagnostics', filesuffix='_2000_def')
ds1 = xr.open_dataset(f)
f = gdir.get_filepath('model_diagnostics', filesuffix='_1920_def')
ds2 = xr.open_dataset(f)

f = 0.9
f = plt.figure(figsize=(9*f, 6*f))
from mpl_toolkits.axes_grid1 import ImageGrid
axs = ImageGrid(f, 111,  # as in plt.subplot(111)
                nrows_ncols=(2, 2),
                axes_pad=0.15,
                share_all=True,
                cbar_location="right",
                cbar_mode="edge",
                cbar_size="7%",
                cbar_pad=0.15,
                )
f.delaxes(axs[0])
f.delaxes(axs[1])
f.delaxes(axs[1].cax)

tx, ty = 0.023, .972
letkm = dict(color='black', ha='left', va='top', fontsize=12,
             bbox=dict(facecolor='white', edgecolor='black'))
llkw = {'interval': 0}

fp = gdir.get_filepath('model_run', filesuffix='_2000_def')
model = FileModel(fp)
model.run_until(800)
ax = axs[3]
graphics.plot_modeloutput_map(gdir, model=model, ax=ax, title='',
                              lonlat_contours_kwargs=llkw, cbar_ax=ax.cax,
                              linewidth=1.,
                              add_scalebar=False, vmax=300)
ax.text(tx, ty, 'c: [1985-2015]', transform=ax.transAxes, **letkm)


fp = gdir.get_filepath('model_run', filesuffix='_1920_def')
model = FileModel(fp)
model.run_until(800)
ax = axs[2]
graphics.plot_modeloutput_map(gdir, model=model, ax=ax, title='',
                              lonlat_contours_kwargs=llkw,
                              add_colorbar=False, linewidth=1.,
                              add_scalebar=False, vmax=300)
ax.text(tx, ty, 'b: [1905-1935]', transform=ax.transAxes, **letkm)

ax = f.add_axes([0.25, 0.57, 0.6, 0.3])
ax.axhline(df.inv_volume_km3.values[0], 0, 800, color='k')
(ds2.volume_m3 * 1e-9).plot(ax=ax, label='[1905-1935]', color='C0')
(ds1.volume_m3 * 1e-9).plot(ax=ax, label='[1985-2015]', color='C3')
ax.set_xlabel('Years')
ax.set_ylabel('Volume [km$^3$]')
ax.legend(loc=[0.65, 0.2])
ax.text(0.012, .965, 'a', transform=ax.transAxes, **letkm)

plt.savefig(fig_path, dpi=150, bbox_inches='tight')
