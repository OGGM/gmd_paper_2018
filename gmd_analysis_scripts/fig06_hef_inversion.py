import os

import matplotlib.pyplot as plt
import numpy as np

import oggm
from oggm import cfg, tasks
from oggm.core.climate import (local_t_star, mu_star_calibration, t_star_from_refmb)
from oggm.core.inversion import (mass_conservation_inversion)
from gmd_analysis_scripts import PLOT_DIR
from oggm.utils import get_rgi_glacier_entities, mkdir, get_rgi_intersects_entities

fig_path = os.path.join(PLOT_DIR, 'hef_inv.pdf')

cfg.initialize()
cfg.PARAMS['border'] = 25

base_dir = os.path.join(os.path.expanduser('~/tmp'), 'OGGM_GMD', 'Invert_hef')
mkdir(base_dir, reset=True)

entity = get_rgi_glacier_entities(['RGI60-11.00897']).iloc[0]
gdir = oggm.GlacierDirectory(entity, base_dir=base_dir)
cfg.set_intersects_db(get_rgi_intersects_entities(['RGI60-11.00897']))

tasks.define_glacier_region(gdir, entity=entity)
tasks.glacier_masks(gdir)
tasks.compute_centerlines(gdir)
tasks.initialize_flowlines(gdir)
tasks.catchment_area(gdir)
tasks.catchment_intersections(gdir)
tasks.catchment_width_geom(gdir)
tasks.catchment_width_correction(gdir)
tasks.process_cru_data(gdir)
local_t_star(gdir)
mu_star_calibration(gdir)

tasks.prepare_for_inversion(gdir)



facs = np.append((np.arange(9)+1)*0.1, (np.arange(19)+2) * 0.5)
vols1 = facs * 0.
vols2 = facs * 0.
vols3 = facs * 0.
vols4 = facs * 0.
vols5 = facs * 0.
vols6 = facs * 0.
vols7 = facs * 0.
vols8 = facs * 0.

glen_a = cfg.PARAMS['glen_a']
fs = 5.7e-20
for i, f in enumerate(facs):
    v, _ = mass_conservation_inversion(gdir, glen_a=glen_a*f)
    vols1[i] = v * 1e-9
    v, _ = mass_conservation_inversion(gdir, glen_a=glen_a*f, fs=fs*0.5)
    vols2[i] = v * 1e-9
    v, a = mass_conservation_inversion(gdir, glen_a=glen_a*f, fs=fs)
    vols3[i] = v * 1e-9


cfg.PARAMS['use_shape_factor_for_inversion'] = 'Adhikari'

for i, f in enumerate(facs):
    # Adhikari
    v, _ = mass_conservation_inversion(gdir, glen_a=glen_a*f)
    vols4[i] = v * 1e-9


tasks.prepare_for_inversion(gdir, invert_with_rectangular=False)
for i, f in enumerate(facs):
    # Parab
    v, _ = mass_conservation_inversion(gdir, glen_a=glen_a * f)
    vols5[i] = v * 1e-9

tasks.prepare_for_inversion(gdir, invert_all_rectangular=True)

for i, f in enumerate(facs):
    # Rect
    v, _ = mass_conservation_inversion(gdir, glen_a=glen_a * f)
    vols6[i] = v * 1e-9

cfg.PARAMS['use_shape_factor_for_inversion'] = None

for i, f in enumerate(facs):
    # Rect no fac
    v, _ = mass_conservation_inversion(gdir, glen_a=glen_a * f)
    vols7[i] = v * 1e-9

tasks.prepare_for_inversion(gdir, invert_with_rectangular=False)

for i, f in enumerate(facs):
    # Parab no fac
    v, _ = mass_conservation_inversion(gdir, glen_a=glen_a * f)
    vols8[i] = v * 1e-9


v_vas = 0.034*((a*1e-6)**1.375)
v_fischer = 0.573

tx, ty = 0.02, .979
letkm = dict(color='black', ha='left', va='top', fontsize=12,
             bbox=dict(facecolor='white', edgecolor='black'))

f = 0.85
f, (ax1, ax2) = plt.subplots(1, 2, figsize=(8*f, 4*f), sharey=True)
cs = plt.get_cmap('Purples')(np.linspace(0.5, 1, 4)[::-1])
lw = 2
alpha = 0.8

ax1.plot(facs, vols4, label='Lateral drag', color=cs[0], linewidth=lw, alpha=alpha)
ax1.plot(facs, vols7, label='Rectangular', color=cs[1], linestyle=':', linewidth=lw, alpha=alpha)
ax1.plot(facs, vols1, label='Default', color=cs[1], linewidth=lw, alpha=alpha)
ax1.plot(facs, vols8, label='Parabolic', color=cs[1], linestyle='--', linewidth=lw, alpha=alpha)
ax1.plot(facs, vols2, label='0.5 f$_s$', color=cs[2], linewidth=lw, alpha=alpha)
ax1.plot(facs, vols3, label='f$_s$', color=cs[3], linewidth=lw, alpha=alpha)

# ax1.plot(facs, vols5, label='Drag parab', color='C0', linestyle=':', linewidth=lw, alpha=alpha)
# ax1.plot(facs, vols6, label='Drag rect', color='C1', linestyle=':', linewidth=lw, alpha=alpha)


ax1.hlines(v_vas, facs[0], facs[-1], linestyles=':',
           label='VAS')
ax1.hlines(v_fischer, facs[0], facs[-1], linestyles='--',
           label='Fischer et al.')
ax1.set_xlabel("A factor")
ax1.set_ylabel("Total volume [km$^3$]")
ax1.set_ylim([0.4, 1.6])
ax1.text(tx, ty, 'a', transform=ax1.transAxes, **letkm)
ax1.legend(loc=1)

facs = np.arange(0.5, 5.01, 0.1)
vols1 = facs * 0.
vols2 = facs * 0.
vols3 = facs * 0.

for i, f in enumerate(facs):
    cfg.PARAMS['prcp_scaling_factor'] = f
    mbdf = gdir.get_ref_mb_data()
    res = t_star_from_refmb(gdir, mbdf=mbdf.ANNUAL_BALANCE)
    local_t_star(gdir, tstar=res['t_star'], bias=res['bias'])
    mu_star_calibration(gdir)
    tasks.prepare_for_inversion(gdir)

    v, _ = mass_conservation_inversion(gdir, glen_a=glen_a)
    vols1[i] = v * 1e-9

    v, _ = mass_conservation_inversion(gdir, glen_a=glen_a*2)
    vols2[i] = v * 1e-9

    v, _ = mass_conservation_inversion(gdir, glen_a=glen_a*4)
    vols3[i] = v * 1e-9


ax2.plot(facs, vols1, label='Default A', color=cs[0], linewidth=lw, alpha=alpha)
ax2.plot(facs, vols2, label='2 A', color=cs[1], linewidth=lw, alpha=alpha)
ax2.plot(facs, vols3, label='4 A', color=cs[2], linewidth=lw, alpha=alpha)
ax2.hlines(v_vas, facs[0], facs[-1], linestyles=':')
ax2.hlines(v_fischer, facs[0], facs[-1], linestyles='--')
ax2.hlines(v_vas, facs[0], facs[-1], linestyles=':',
           label='VAS')
ax2.hlines(v_fischer, facs[0], facs[-1], linestyles='--',
           label='Fischer et al.')
ax2.set_xlabel("Precipitation factor")
ax2.text(tx, ty, 'b', transform=ax2.transAxes, **letkm)
ax2.legend(loc=1)

plt.tight_layout()
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
