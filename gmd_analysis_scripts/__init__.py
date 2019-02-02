import os
PLOT_DIR = os.path.join(os.path.dirname(__file__), 'output_plots')
DATA_DIR = '/home/mowglie/disk/OGGM_Runs/GMD_Paper/'

from oggm.utils import mkdir
mkdir(PLOT_DIR)

import seaborn as sns
LCMAP = sns.hls_palette(8, l=.45, s=.6)
