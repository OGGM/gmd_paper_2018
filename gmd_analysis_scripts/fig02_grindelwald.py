import os

import matplotlib.pyplot as plt
import netCDF4
import numpy as np

import oggm
from oggm import cfg, tasks, graphics
from gmd_analysis_scripts import PLOT_DIR
from oggm.utils import (nicenumber, mkdir, get_rgi_glacier_entities,
                        get_rgi_intersects_entities)

cfg.initialize()
cfg.PARAMS['border'] = 10

fig_path = os.path.join(PLOT_DIR, 'grindelwald.pdf')

base_dir = os.path.join(os.path.expanduser('~/tmp'), 'OGGM_GMD', 'Grindelwald')
cfg.PATHS['working_dir'] = base_dir
mkdir(base_dir, reset=True)

rgidf = get_rgi_glacier_entities(['RGI60-11.01270'])
entity = rgidf.iloc[0]
gdir = oggm.GlacierDirectory(entity, base_dir=base_dir)

cfg.set_intersects_db(get_rgi_intersects_entities(['RGI60-11.01270']))

tasks.define_glacier_region(gdir, entity=entity)
tasks.glacier_masks(gdir)
tasks.compute_centerlines(gdir)
tasks.initialize_flowlines(gdir)
tasks.compute_downstream_line(gdir)
tasks.catchment_area(gdir)
tasks.catchment_intersections(gdir)
tasks.catchment_width_geom(gdir)
tasks.catchment_width_correction(gdir)

with netCDF4.Dataset(gdir.get_filepath('gridded_data')) as nc:
    mask = nc.variables['glacier_mask'][:]
    topo = nc.variables['topo_smoothed'][:]
rhgt = topo[np.where(mask)][:]
hgt, harea = gdir.get_inversion_flowline_hw()

# Check for area distrib
bins = np.arange(nicenumber(np.min(hgt), 150, lower=True),
                 nicenumber(np.max(hgt), 150) + 1,
                 150.)
h1, b = np.histogram(hgt, weights=harea, density=True, bins=bins)
h2, b = np.histogram(rhgt, density=True, bins=bins)

h1 = h1 / np.sum(h1)
h2 = h2 / np.sum(h2)

LCMAP = plt.get_cmap('Purples')(np.linspace(0.4, 1, 5)[::-1])
MCMAP = graphics.truncate_colormap(plt.get_cmap('Blues'), 0.2, 0.8, 255)

f, axs = plt.subplots(2, 2, figsize=(8.5, 7))
axs = np.asarray(axs).flatten()

llkw = {'interval': 0}
letkm = dict(color='black', ha='right', va='top', fontsize=12,
             bbox=dict(facecolor='white', edgecolor='black'))
xt, yt = 109, 2.

im = graphics.plot_catchment_areas(gdir, ax=axs[0], title='',
                                   lonlat_contours_kwargs=llkw,
                                   add_scalebar=True, lines_cmap=LCMAP,
                                   mask_cmap=MCMAP)

axs[0].text(xt, yt, 'a', **letkm)

graphics.plot_catchment_width(gdir, ax=axs[1], title='', add_colorbar=False,
                              lonlat_contours_kwargs=llkw,
                              add_scalebar=False, lines_cmap=LCMAP)
axs[1].text(xt, yt, 'b', **letkm)

graphics.plot_catchment_width(gdir, ax=axs[2], title='', corrected=True,
                              add_colorbar=False,
                              lonlat_contours_kwargs=llkw,
                              add_scalebar=False, add_touches=True,
                              lines_cmap=LCMAP)
axs[2].text(xt, yt, 'c', **letkm)

width = 0.6 * (bins[1] - bins[0])
center = (bins[:-1] + bins[1:]) / 2
axs[3].bar(center, h2, align='center', width=width, alpha=0.5, color='C0', label='SRTM')
axs[3].bar(center, h1, align='center', width=width, alpha=0.5, color='C3', label='OGGM')
axs[3].set_xlabel('Altitude (m)')
plt.legend(loc='best')
axs[3].text(3775, 0.223, 'd', **letkm)

dy = np.abs(np.diff(axs[3].get_ylim()))
dx = np.abs(np.diff(axs[3].get_xlim()))
aspect0 = topo.shape[0] / topo.shape[1]
aspect = aspect0 / (float(dy) / dx)
axs[3].set_aspect(aspect)

# plt.tight_layout()
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
