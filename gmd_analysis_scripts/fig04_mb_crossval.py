# Python imports
import os

# Libs
import numpy as np
import pandas as pd
import geopandas as gpd

# Locals
from gmd_analysis_scripts import PLOT_DIR
from oggm import cfg, workflow, tasks, utils
from oggm.core.massbalance import PastMassBalance, MultipleFlowlineMassBalance
import matplotlib.pyplot as plt

fig_path = os.path.join(PLOT_DIR, 'mb_crossval.pdf')

# RGI Version
rgi_version = '61'

# Initialize OGGM and set up the run parameters
cfg.initialize()

# Local paths (where to find the OGGM run output)
WORKING_DIR = os.path.join(os.path.expanduser('~/tmp'), 'OGGM_GMD',
                           'OGGM_ref_mb_RGIV{}'.format(rgi_version))
cfg.PATHS['working_dir'] = WORKING_DIR

# Read the rgi file
rgidf = gpd.read_file(os.path.join(WORKING_DIR, 'mb_ref_glaciers.shp'))

# Go - initialize working directories
gdirs = workflow.init_glacier_regions(rgidf)

# Go - initialize glacier directories
gdirs = workflow.init_glacier_regions(rgidf)

# Cross-validation
file = os.path.join(cfg.PATHS['working_dir'], 'ref_tstars.csv')
ref_df = pd.read_csv(file, index_col=0)
for i, gdir in enumerate(gdirs):

    # Calibrate the model in a standard way
    tasks.local_t_star(gdir, ref_df=ref_df)
    tasks.mu_star_calibration(gdir)
    _df = gdir.read_json('local_mustar')
    ref_df.loc[gdir.rgi_id, 'mustar'] = _df['mu_star_glacierwide']

for i, gdir in enumerate(gdirs):

    print('Cross-validation iteration {} of {}'.format(i + 1, len(ref_df)))

    # Now recalibrate the model blindly
    tmp_ref_df = ref_df.loc[ref_df.index != gdir.rgi_id]
    tasks.local_t_star(gdir, ref_df=tmp_ref_df)
    tasks.mu_star_calibration(gdir)

    # Mass-balance model with cross-validated parameters instead
    mb_mod = MultipleFlowlineMassBalance(gdir, mb_model_class=PastMassBalance,
                                         use_inversion_flowlines=True)

    # Mass-balance timeseries, observed and simulated
    refmb = gdir.get_ref_mb_data().copy()
    refmb['OGGM'] = mb_mod.get_specific_mb(year=refmb.index)

    # Compare their standard deviation
    std_ref = refmb.ANNUAL_BALANCE.std()
    rcor = np.corrcoef(refmb.OGGM, refmb.ANNUAL_BALANCE)[0, 1]
    if std_ref == 0:
        # I think that such a thing happens with some geodetic values
        std_ref = refmb.OGGM.std()
        rcor = 1

    # Store the scores
    ref_df.loc[gdir.rgi_id, 'CV_MB_BIAS'] = (refmb.OGGM.mean() -
                                             refmb.ANNUAL_BALANCE.mean())
    ref_df.loc[gdir.rgi_id, 'CV_MB_SIGMA_BIAS'] = (refmb.OGGM.std() / std_ref)
    ref_df.loc[gdir.rgi_id, 'CV_MB_COR'] = rcor

    # Now naively interpolate the mu* instead
    # Compute the distance to each glacier
    distances = utils.haversine(gdir.cenlon, gdir.cenlat,
                                tmp_ref_df.lon, tmp_ref_df.lat)

    # Take the 10 closest
    aso = np.argsort(distances)[0:9]
    amin = tmp_ref_df.iloc[aso]
    distances = distances[aso] ** 2

    # If really close no need to divide, else weighted average
    if distances.iloc[0] <= 0.1:
        mustar = amin.mustar.iloc[0]
        bias = amin.bias.iloc[0]
    else:
        mustar = np.average(amin.mustar, weights=1./distances)
        bias = np.average(amin.bias, weights=1./distances)

    # Mass-balance model with inerpolated parameters instead
    mb_mod = PastMassBalance(gdir, mu_star=mustar, bias=bias)
    h, w = gdir.get_inversion_flowline_hw()
    refmb['INTERP'] = mb_mod.get_specific_mb(h, w, year=refmb.index)

    # Store the scores
    ref_df.loc[gdir.rgi_id, 'INTERP_MB_BIAS'] = (refmb.INTERP.mean() -
                                                 refmb.ANNUAL_BALANCE.mean())



# Write out
ref_df.to_csv(os.path.join(cfg.PATHS['working_dir'], 'crossval_tstars.csv'))

# Marzeion et al Figure 3
f = 1.3
f, (ax1, ax2) = plt.subplots(1, 2, figsize=(6*f, 2.3*f), sharey=True)
bins = np.arange(24) * 400 - 4600
ref_df['CV_MB_BIAS'].plot(ax=ax1, kind='hist', bins=bins, color='C3', label='')
ax1.vlines(ref_df['CV_MB_BIAS'].mean(), 0, 120, linestyles='--', label='Mean')
ax1.vlines(ref_df['CV_MB_BIAS'].quantile(), 0, 120, label='Median')
ax1.vlines(ref_df['CV_MB_BIAS'].quantile([0.05, 0.95]), 0, 120, color='grey',
                                       label='5% and 95%\npercentiles')
ax1.text(0.01, 0.99, 'N = {}'.format(len(gdirs)),
         horizontalalignment='left',
         verticalalignment='top',
         transform=ax1.transAxes)

ax1.set_ylim(0, 120)
ax1.set_xlim(-5000, 5000)
ax1.set_ylabel('N Glaciers')
ax1.set_xlabel('Mass-balance error (mm w.e. yr$^{-1}$)')
ax1.legend(loc='best', fontsize=7.5)
ref_df['INTERP_MB_BIAS'].plot(ax=ax2, kind='hist', bins=bins, color='C0')
ax2.vlines(ref_df['INTERP_MB_BIAS'].mean(), 0, 120, linestyles='--')
ax2.vlines(ref_df['INTERP_MB_BIAS'].quantile(), 0, 120)
ax2.vlines(ref_df['INTERP_MB_BIAS'].quantile([0.05, 0.95]), 0, 120, color='grey')
ax2.set_xlabel('Mass-balance error (mm w.e. yr$^{-1}$)')
ax2.set_xlim(-5000, 5000)

plt.savefig(fig_path, dpi=150, bbox_inches='tight')

scores = 'Median bias: {:.2f}\n'.format(ref_df['CV_MB_BIAS'].median())
scores += 'Mean bias: {:.2f}\n'.format(ref_df['CV_MB_BIAS'].mean())
scores += 'RMS: {:.2f}\n'.format(np.sqrt(np.mean(ref_df['CV_MB_BIAS']**2)))
scores += 'Sigma bias: {:.2f}\n'.format(np.mean(ref_df['CV_MB_SIGMA_BIAS']))

# Output
print(scores)
fn = os.path.join(WORKING_DIR, 'scores.txt')
with open(fn, 'w') as f:
    f.write(scores)
