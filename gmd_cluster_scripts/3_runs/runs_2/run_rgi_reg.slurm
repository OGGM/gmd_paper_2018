#!/bin/bash
#
#SBATCH --job-name=oggm_rgi_reg_model
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --time=48:00:00
#SBATCH --mail-user=fabien.maussion@uibk.ac.at
#SBATCH --mail-type=ALL

# Abort whenever a single step fails. Without this, bash will just continue on errors.
set -e

# Load the required environment modules for OGGM
module load python/3.6.1 oggm-binary-deps/1

# Activate our local OGGM virtualenv
source ~/oggm_venv/bin/activate

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

# Run the actual job. The srun invocation starts it as individual step for slurm.
srun -n 1 -c "${SLURM_JOB_CPUS_PER_NODE}" python3 ./model_rgi_reg.py

echo "Start copying..."

# Once a slurm job is done, slurm will clean up the /work directory on that node from any leftovers from that user.
# So copy any result data you need from there back to your home dir!
# $SLURM_SUBMIT_DIR points to the directory from where the job was initially commited.
OUTDIR=/home/users/fmaussion/run_output/

# Copy any neccesary result data.
cp "${WORKDIR}/"run_output*.nc "${OUTDIR}/rgi_reg_$RGI_REG/"
cp "${WORKDIR}/"task_log*.csv "${OUTDIR}/rgi_reg_$RGI_REG/"


# Print a final message so you can actually see it being done in the output log.
echo "SLURM DONE"
