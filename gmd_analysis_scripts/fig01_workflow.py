import os
import matplotlib.pyplot as plt
import tempfile

import oggm
from oggm import cfg, tasks, graphics
from gmd_analysis_scripts import PLOT_DIR
from oggm import utils

dir_path = os.path.join(tempfile.gettempdir(), 'fig_01')
fig_path = os.path.join(PLOT_DIR, 'workflow_tas.pdf')

cfg.initialize()
cfg.PARAMS['border'] = 20

cfg.PATHS['working_dir'] = dir_path
utils.mkdir(dir_path, reset=True)

rgidf = utils.get_rgi_glacier_entities(['RGI60-18.02342'])
entity = rgidf.iloc[0]

cfg.set_intersects_db(utils.get_rgi_intersects_entities(['RGI60-18.02342']))

gdir = oggm.GlacierDirectory(entity, base_dir=dir_path)

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

glen_a = cfg.PARAMS['glen_a']
tasks.prepare_for_inversion(gdir)
tasks.mass_conservation_inversion(gdir, glen_a=glen_a, fs=0)
tasks.filter_inversion_output(gdir)

# run
tasks.init_present_time_glacier(gdir)
tasks.run_random_climate(gdir, bias=0., temperature_bias=-1,
                         nyears=120, glen_a=glen_a,
                         check_for_boundaries=False)

f = 0.9
f = plt.figure(figsize=(7, 10))
from mpl_toolkits.axes_grid1 import ImageGrid

axs = ImageGrid(f, 111,  # as in plt.subplot(111)
                nrows_ncols=(3, 2),
                axes_pad=0.15,
                share_all=True,
                cbar_location="right",
                cbar_mode="edge",
                cbar_size="7%",
                cbar_pad=0.15,
                )

llkw = {'interval': 0}
letkm = dict(color='black', ha='left', va='top', fontsize=16,
             bbox=dict(facecolor='white', edgecolor='black'))

graphics.plot_domain(gdir, ax=axs[0], title='', add_colorbar=False,
                     lonlat_contours_kwargs=llkw)
xt, yt = 4.5, 4.5
axs[0].text(xt, yt, 'a', **letkm)

im = graphics.plot_centerlines(gdir, ax=axs[1], title='', add_colorbar=True,
                               lonlat_contours_kwargs=llkw, cbar_ax=axs[1].cax,
                               add_scalebar=False)
axs[1].text(xt, yt, 'b', **letkm)

graphics.plot_catchment_width(gdir, ax=axs[2], title='', add_colorbar=False,
                              lonlat_contours_kwargs=llkw,
                              add_scalebar=False)
axs[2].text(xt, yt, 'c', **letkm)

graphics.plot_catchment_width(gdir, ax=axs[3], title='', corrected=True,
                              add_colorbar=False,
                              lonlat_contours_kwargs=llkw,
                              add_scalebar=False)
axs[3].text(xt, yt, 'd', **letkm)

f.delaxes(axs[3].cax)

graphics.plot_inversion(gdir, ax=axs[4], title='', linewidth=1.3,
                        add_colorbar=False, vmax=650,
                        lonlat_contours_kwargs=llkw,
                        add_scalebar=False)
axs[4].text(xt, yt, 'e', **letkm)

graphics.plot_modeloutput_map(gdir, ax=axs[5], modelyr=100, title='',
                              linewidth=1.3, add_colorbar=True,
                              cbar_ax=axs[5].cax, vmax=650,
                              lonlat_contours_kwargs=llkw,
                              add_scalebar=False)
axs[5].text(xt, yt, 'f', **letkm)

plt.savefig(fig_path, dpi=150, bbox_inches='tight')
