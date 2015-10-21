#!/bin/sh 

echo ''
echo '*** Checking -edit file ***'
echo ''
chado_load_checks.pl fbdv/src/trunk/ontologies/fbdv-edit.obo > fbdv-edit_checks.txt
echo ''
echo '*** Generating potential release ***'
echo "*** Generating release files using the $REASONER reasoner ***"
echo ''
ontology-release-runner --reasoner $REASONER --allow-equivalent-pairs fbdv/src/trunk/ontologies/fbdv-edit.obo --no-subsets --simple --relaxed --asserted --allow-overwrite --outdir oort
echo ''
echo '*** Running tests on new fbdv-simple.obo ***'
echo '*** chado load checks ***'
echo ''
chado_load_checks.pl oort/fbdv-simple.obo > oort/chado_load_checks_out.txt # Dump to oort folder so in-place for release.
echo ''
echo '*** Grabbing latest fbdv-simple.obo ***'
echo ''
# Grabs latest -simple from obolibrary purl.  -r is used as it stomps on last downloaded version.
wget -r http://purl.obolibrary.org/obo/fbdv/fbdv-simple.obo
echo ''
echo '*** Comparing to current public version, logging name and ID changes. ***'
echo ''
obo_track_new.pl purl.obolibrary.org/obo/fbdv/fbdv-simple.obo oort/fbdv-simple.obo > oort/obo_track_out.txt # Dump to oort folder so in-place for release.
rm purl.obolibrary.org/obo/fbdv/fbdv-simple.obo # Cleaning up
echo ''
echo '*** Calculating new metrics ***'
onto_metrics_calc.pl 'FlyBase development CV' oort/fbdv-non-classified.obo > oort/fbdv_metrics.txt  # Dump to oort folder so in-place for release.
