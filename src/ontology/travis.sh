# TRAVIS checks - only required reports, no imports/patterns
set -e

sh run.sh make MIR=false IMP=false PAT=false travis_checks -B
