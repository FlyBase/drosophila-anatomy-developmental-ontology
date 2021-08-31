# Running the DPO release pipeline for TRAVIS
set -e

sh run.sh make IMP=false PAT=false pre_release -B

sh run.sh make SRC=fbbt-edit-release.owl IMP=false PAT=false prepare_release -B

sh run.sh make IMP=false PAT=false flybase_qc -B
