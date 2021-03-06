import os

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import shapely.geometry as shpg

import oggm
from oggm import cfg, tasks
from oggm.core.centerlines import (Centerline)
from oggm.core.flowline import (FluxBasedModel)
from oggm.core.inversion import (mass_conservation_inversion)
from oggm.core.massbalance import (LinearMassBalance)
from gmd_analysis_scripts import PLOT_DIR
from oggm.utils import get_demo_file, mkdir

# test directory
base_dir = os.path.join(os.path.expanduser('~/tmp'), 'OGGM_GMD', 'Inversions')
mkdir(base_dir, reset=True)

fig_path = os.path.join(PLOT_DIR, 'inversions.pdf')

# Init
cfg.initialize()
cfg.PARAMS['use_intersects'] = False

entity = gpd.read_file(get_demo_file('Hintereisferner_RGI5.shp')).iloc[0]
gdir = oggm.GlacierDirectory(entity, base_dir=base_dir)
tasks.define_glacier_region(gdir, entity=entity)

# Models
from oggm.tests.test_models import (dummy_constant_bed, dummy_noisy_bed,
                                    dummy_constant_bed_cliff)

# Figure
f = 0.7
f, axs = plt.subplots(2, 2, figsize=(10*f, 7*f), sharey=True, sharex=True)
axs = np.asarray(axs).flatten()

tx, ty = .98, .97
letkm = dict(color='black', ha='right', va='top', fontsize=12,
             bbox=dict(facecolor='white', edgecolor='black'))

fls = dummy_constant_bed(map_dx=gdir.grid.dx)
mb = LinearMassBalance(2600.)
model = FluxBasedModel(fls, mb_model=mb, y0=0.)
model.run_until_equilibrium()
fls = []
for fl in model.fls:
    pg = np.where(fl.thick > 0)
    line = shpg.LineString([fl.line.coords[int(p)] for p in pg[0]])
    flo = Centerline(line, dx=fl.dx, surface_h=fl.surface_h[pg])
    flo.widths = fl.widths[pg]
    flo.is_rectangular = np.ones(flo.nx).astype(np.bool)
    fls.append(flo)

gdir.write_pickle(fls, 'inversion_flowlines')
tasks.apparent_mb_from_linear_mb(gdir)
tasks.prepare_for_inversion(gdir)
v, _ = mass_conservation_inversion(gdir)
np.testing.assert_allclose(v, model.volume_m3, rtol=0.05)
inv = gdir.read_pickle('inversion_output')[-1]
# plot
ax = axs[0]
thick1 = inv['thick']
pg = model.fls[-1].thick > 0
bh = model.fls[-1].bed_h[pg]
sh = model.fls[-1].surface_h[pg]
ax.plot(sh, 'k', label='Glacier surface')
ax.plot(bh, 'C0', label='Real bed', linewidth=2)
ax.plot(sh - thick1, 'C3', label='Computed bed')
ax.set_ylabel('Elevation [m]')
ax.set_ylim([1950, 3100])
ax.legend(loc=3)
ax.text(tx, ty, 'a', transform=ax.transAxes, **letkm)

fls = dummy_constant_bed_cliff(map_dx=gdir.grid.dx, cliff_height=120)
mb = LinearMassBalance(2600.)
model = FluxBasedModel(fls, mb_model=mb, y0=0.)
model.run_until_equilibrium()
fls = []
for fl in model.fls:
    pg = np.where(fl.thick > 0)
    line = shpg.LineString([fl.line.coords[int(p)] for p in pg[0]])
    flo = Centerline(line, dx=fl.dx, surface_h=fl.surface_h[pg])
    flo.widths = fl.widths[pg]
    flo.is_rectangular = np.ones(flo.nx).astype(np.bool)
    fls.append(flo)
gdir.write_pickle(fls, 'inversion_flowlines')
tasks.apparent_mb_from_linear_mb(gdir)
tasks.prepare_for_inversion(gdir)
v, _ = mass_conservation_inversion(gdir)
np.testing.assert_allclose(v, model.volume_m3, rtol=0.05)
inv = gdir.read_pickle('inversion_output')[-1]
# plot
ax = axs[1]
thick1 = inv['thick']
pg = model.fls[-1].thick > 0
bh = model.fls[-1].bed_h[pg]
sh = model.fls[-1].surface_h[pg]
ax.plot(sh, 'k')
ax.plot(bh, 'C0', label='Real bed', linewidth=2)
ax.plot(sh - thick1, 'C3', label='Computed bed')
ax.text(tx, ty, 'b', transform=ax.transAxes, **letkm)

fls = dummy_noisy_bed(map_dx=gdir.grid.dx)
mb = LinearMassBalance(2600.)
model = FluxBasedModel(fls, mb_model=mb, y0=0.)
model.run_until_equilibrium()
fls = []
for fl in model.fls:
    pg = np.where(fl.thick > 0)
    line = shpg.LineString([fl.line.coords[int(p)] for p in pg[0]])
    flo = Centerline(line, dx=fl.dx, surface_h=fl.surface_h[pg])
    flo.widths = fl.widths[pg]
    flo.is_rectangular = np.ones(flo.nx).astype(np.bool)
    fls.append(flo)

gdir.write_pickle(fls, 'inversion_flowlines')
tasks.apparent_mb_from_linear_mb(gdir)
tasks.prepare_for_inversion(gdir)
v, _ = mass_conservation_inversion(gdir)
np.testing.assert_allclose(v, model.volume_m3, rtol=0.05)
inv = gdir.read_pickle('inversion_output')[-1]
# plot
ax = axs[2]
thick1 = inv['thick']
pg = model.fls[-1].thick > 0
bh = model.fls[-1].bed_h[pg]
sh = model.fls[-1].surface_h[pg]
ax.plot(sh, 'k')
ax.plot(bh, 'C0', label='Real bed', linewidth=2)
ax.plot(sh - thick1, 'C3', label='Computed bed')
ax.set_xlabel('Grid [dx]')
ax.set_ylabel('Elevation [m]')
ax.text(tx, ty, 'c', transform=ax.transAxes, **letkm)

#
fls = dummy_constant_bed(map_dx=gdir.grid.dx)
mb = LinearMassBalance(2600.)
model = FluxBasedModel(fls, mb_model=mb, y0=0.)
model.run_until_equilibrium()
mb = LinearMassBalance(2800.)
model = FluxBasedModel(model.fls, mb_model=mb, y0=0)
model.run_until(60)
fls = []
for fl in model.fls:
    pg = np.where(fl.thick > 0)
    line = shpg.LineString([fl.line.coords[int(p)] for p in pg[0]])
    sh = fl.surface_h[pg]
    flo = Centerline(line, dx=fl.dx, surface_h=sh)
    flo.widths = fl.widths[pg]
    flo.is_rectangular = np.ones(flo.nx).astype(np.bool)
    fls.append(flo)

gdir.write_pickle(fls, 'inversion_flowlines')
tasks.apparent_mb_from_linear_mb(gdir)
tasks.prepare_for_inversion(gdir)
v, _ = mass_conservation_inversion(gdir)
# expected errors
assert v > model.volume_m3
print('Error:', v / model.volume_m3 * 100)

inv = gdir.read_pickle('inversion_output')[-1]
# plot
ax = axs[3]
thick1 = inv['thick']
pg = model.fls[-1].thick > 0
bh = model.fls[-1].bed_h[pg]
sh = model.fls[-1].surface_h[pg]
ax.plot(sh, 'k')
ax.plot(bh, 'C0', label='Real bed', linewidth=2)
ax.plot(sh - thick1, 'C3', label='Computed bed')
ax.set_xlabel('Grid [dx]')
ax.text(tx, ty, 'd', transform=ax.transAxes, **letkm)

plt.tight_layout()
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
