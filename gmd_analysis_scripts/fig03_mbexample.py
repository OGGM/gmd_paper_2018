import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

import oggm
from oggm import cfg, tasks
from oggm.core.climate import (mb_yearly_climate_on_glacier,
                               t_star_from_refmb, local_t_star,
                               )
from gmd_analysis_scripts import PLOT_DIR
from oggm.utils import mkdir, get_rgi_glacier_entities

fig_path = os.path.join(PLOT_DIR, 'mb_ex.pdf')

cfg.initialize()
cfg.PARAMS['use_intersects'] = False

base_dir = os.path.join(os.path.expanduser('~/tmp'), 'OGGM_GMD', 'MB')
mkdir(base_dir, reset=True)

entity = get_rgi_glacier_entities(['RGI60-11.00897']).iloc[0]
gdir = oggm.GlacierDirectory(entity, base_dir=base_dir, reset=True)

tasks.define_glacier_region(gdir, entity=entity)
tasks.glacier_masks(gdir)
tasks.compute_centerlines(gdir)
tasks.initialize_flowlines(gdir)
tasks.catchment_area(gdir)
tasks.catchment_width_geom(gdir)
tasks.catchment_width_correction(gdir)

tasks.process_cru_data(gdir)
tasks.glacier_mu_candidates(gdir)

mbdf = gdir.get_ref_mb_data()
res = t_star_from_refmb(gdir, mbdf=mbdf.ANNUAL_BALANCE)
local_t_star(gdir, tstar=res['t_star'], bias=res['bias'], reset=True)

# For plots
mu_yr_clim = gdir.read_pickle('climate_info')['mu_candidates_glacierwide']
years, temp_yr, prcp_yr = mb_yearly_climate_on_glacier(gdir)

# which years to look at
selind = np.searchsorted(years, mbdf.index)
temp_yr = np.mean(temp_yr[selind])
prcp_yr = np.mean(prcp_yr[selind])

# Average oberved mass-balance
ref_mb = mbdf.ANNUAL_BALANCE.mean()
mb_per_mu = prcp_yr - mu_yr_clim * temp_yr

# Diff to reference
diff = mb_per_mu - ref_mb
pdf = pd.DataFrame()
pdf[r'$\mu (t)$'] = mu_yr_clim
pdf['bias'] = diff

# plot functions
f = 0.7
f, axs = plt.subplots(3, 1, figsize=(8*f, 10*f), sharex=True)

d = xr.open_dataset(gdir.get_filepath('climate_monthly'))
d['year'] = ('time', np.repeat(np.arange(d['time.year'][0]+1, d['time.year'][-1]+1), 12))


temp = d.temp.groupby(d.year).mean().to_series()
del temp.index.name
prcp = d.prcp.groupby(d.year).sum().to_series()
del prcp.index.name

c = 'DimGrey'
cl = 'k'

letkm = dict(color='black', ha='left', va='bottom', fontsize=12,
             bbox=dict(facecolor='white', edgecolor='black'))
xt, yt = 0.015, 0.03

temp.plot(ax=axs[0], label='Annual temp', color=c)
temp.rolling(31, center=True, min_periods=15).mean().plot(ax=axs[0], linewidth=2,
                                                          color=cl,
                                                          label='31-yr avg')
axs[0].legend(loc='best')
axs[0].set_ylabel(r'°C')
axs[0].set_xlim(1901, 2015)
axs[0].text(xt, yt, 'a', **letkm, transform=axs[0].transAxes)

prcp.plot(ax=axs[1], label='Annual prcp', color=c)
prcp.rolling(31, center=True, min_periods=15).mean().plot(ax=axs[1], linewidth=2,
                                                          color=cl,
                                                          label='31-yr avg')
axs[1].legend(loc='best')
axs[1].set_ylabel(r'mm yr$^{-1}$')
axs[1].text(xt, yt, 'b', **letkm, transform=axs[1].transAxes)

pdf[r'$\mu (t)$'].plot(ax=axs[2], linewidth=2, color='C0')
axsup = pdf['bias'].plot(ax=axs[2], secondary_y=True, linewidth=2, color='C3',
                         label='bias')

plt.hlines(0, 1901, 2015, linestyles='-')
axs[2].set_ylabel(r'$\mu$ (mm yr$^{-1}$ K$^{-1}$)')
plt.ylabel(r'bias (mm w.e. yr$^{-1}$)')
yl = plt.gca().get_ylim()
plt.plot((res['t_star'], res['t_star']), (yl[0], 0), linestyle=':', color='grey')
plt.ylim(yl)
axs[2].text(xt, yt, 'c', **letkm, transform=axs[2].transAxes)

handles, labels = [],[]
for ax in [axs[2], axsup]:
    for h,l in zip(*ax.get_legend_handles_labels()):
        handles.append(h)
        labels.append(l)
plt.legend(handles, labels, loc=9, ncol=2)

plt.tight_layout()
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
