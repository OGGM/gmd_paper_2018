#!/bin/bash
#
#SBATCH --job-name=gmd_paper_dyn
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --time=48:00:00
#SBATCH --mail-user=fabien.maussion@uibk.ac.at
#SBATCH --mail-type=ALL

# Abort whenever a single step fails. Without this, bash will just continue on errors.
set -e

# Current RGI region
RGI_REG=`printf "%02d" $SLURM_ARRAY_TASK_ID`
export RGI_REG

# On every node, when slurm starts a job, it will make sure the directory
# /work/username exists and is writable by the jobs user.
# We create a sub-directory there for this job to store its runtime data at.
WORKDIR="/work/$SLURM_JOB_USER/$SLURM_JOB_ID/rgi_reg_$RGI_REG"
mkdir -p "$WORKDIR"
echo "RGI Region: $RGI_REG"
echo "Workdir for this run: $WORKDIR"

# Export the WORKDIR as environment variable so our script can use it to find its working directory.
export WORKDIR

# Use the local data download cache
export OGGM_DOWNLOAD_CACHE=/home/data/download
export OGGM_DOWNLOAD_CACHE_RO=1
export OGGM_EXTRACT_DIR="/work/$SLURM_JOB_USER/$SLURM_JOB_ID/oggm_tmp"

# All commands in the EOF block run inside of the container
# Adjust container version to your needs, they are guaranteed to never change after their respective day has passed.
srun -n 1 -c "${SLURM_JOB_CPUS_PER_NODE}" singularity exec docker://oggm/oggm:20181123 bash -s <<EOF
  set -e
  # Setup a fake home dir inside of our workdir, so we don't clutter the actual shared homedir with potentially incompatible stuff.
  export HOME="$WORKDIR/fake_home"
  mkdir "\$HOME"
  # Create a venv that _does_ use system-site-packages, since everything is already installed on the container.
  # We cannot work on the container itself, as the base system is immutable.
  python3 -m venv --system-site-packages "$WORKDIR/oggm_env"
  source "$WORKDIR/oggm_env/bin/activate"
  # Make sure latest pip is installed
  pip install --upgrade pip setuptools
  # Install a fixed OGGM version
  pip install --upgrade "git+https://github.com/OGGM/oggm.git@a74695fcaba0fc50580109bb578ff64df51b3f62"
  # pip install "git+https://github.com/fmaussion/oggm.git@dev"
  # Finally, the run
  python3 ./run.py
EOF

echo "Start copying..."

# Once a slurm job is done, slurm will clean up the /work directory on that node from any leftovers from that user.
# So copy any result data you need from there back to your home dir!
# $SLURM_SUBMIT_DIR points to the directory from where the job was initially commited.
OUTDIR=/home/users/fmaussion/gmd_run_output/

# Copy any necesary result data.
mkdir -p "${OUTDIR}/rgi_reg_$RGI_REG/"
cp "${WORKDIR}/"run_output*.nc "${OUTDIR}/rgi_reg_$RGI_REG/"
cp "${WORKDIR}/"task_log*.csv "${OUTDIR}/rgi_reg_$RGI_REG/"

# Print a final message so you can actually see it being done in the output log.
echo "SLURM DONE"
