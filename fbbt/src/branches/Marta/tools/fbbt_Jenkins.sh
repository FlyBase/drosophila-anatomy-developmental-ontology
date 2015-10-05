echo ''
echo '*** Checking -edit file ***'
echo ''
chado_load_checks.pl ontologies/fbbt-edit.obo > fbbt-edit_checks.txt
echo ''
echo '*** Generating potential release ***'
echo '** Rolling autodefs **'
update_EC_defs.pl ontologies/fbbt-edit.obo > tmp.obo
echo ''
echo '*** Merging source file ***'
echo ''
owltools tmp.obo --merge ontologies/fbbt_auth_attrib_licence.owl --merge ontologies/fbbt-ext.owl -o file://`pwd`/fbbt-edit_merged.owl
rm tmp.obo # Cleaning up
echo ''
echo "*** Generating release files using the $REASONER reasoner ***"
echo ''
ontology-release-runner --reasoner $REASONER fbbt-edit_merged.owl --no-subsets --simple --relaxed --asserted --allow-overwrite --outdir oort
echo ''
echo '*** Running tests on new fbbt-simple.obo ***'
echo '*** chado load checks ***'
echo ''
chado_load_checks.pl oort/fbbt-simple.obo > oort/chado_load_checks_out.txt # Dump to oort folder so in-place for release.
echo ''
echo '*** Grabbing latest fbbt-simple.obo ***'
echo ''
# Grabs latest -simple from obolibrary purl.  -r is used as it stomps on last downloaded version.
wget -r http://purl.obolibrary.org/obo/fbbt/fbbt-simple.obo
echo ''
echo '*** Comparing to current public version, logging name and ID changes. ***'
echo ''
obo_track_new.pl purl.obolibrary.org/obo/fbbt/fbbt-simple.obo oort/fbbt-simple.obo > oort/obo_track_out.txt # Dump to oort folder so in-place for release.
rm purl.obolibrary.org/obo/fbbt/fbbt-simple.obo # Cleaning up
echo ''
echo '*** Calculating new metrics ***'
onto_metrics_calc.pl fly_anatomy.ontology oort/fbbt-non-classified.obo > oort/fbbt_metrics.txt  # Dump to oort folder so in-place for release.