# TRAVIS checks - only required reports, no imports/patterns
# Travis is disabled (standby CI); see ../../.travis.yml for how to reactivate.
# The same checks can be run locally with: sh travis.sh
set -e

sh run.sh make MIR=false IMP=false PAT=false travis_checks -B
