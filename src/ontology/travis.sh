# Running the DPO release pipeline for TRAVIS
set -e

sh run.sh make IMP=false PAT=false prepare_release -B
