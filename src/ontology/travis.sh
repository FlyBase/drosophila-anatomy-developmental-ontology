# Running the DPO release pipeline for TRAVIS
set -e

sh run.sh make pre_release -B

sh run.sh make SRC=fbbt-edit-release.owl IMP=false prepare_release -B

sh run.sh make flybase_qc -B
