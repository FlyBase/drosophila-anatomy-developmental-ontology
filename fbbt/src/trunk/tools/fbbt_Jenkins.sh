echo ''
echo '*** Checking -edit file ***'
echo ''
chado_load_checks.pl fbbt/src/trunk/ontologies/fbbt-edit.obo > fbbt-edit_checks.txt
echo ''
echo '*** Generating potential release ***'
echo '** Rolling autodefs **'
update_EC_defs.pl fbbt/src/trunk/ontologies/fbbt-edit.obo > tmp.obo
echo ''
echo '*** Merging source file ***'
echo ''
owltools tmp.obo --merge fbbt/src/trunk/ontologies/fbbt_auth_attrib_licence.owl --merge fbbt/src/trunk/ontologies/fbbt-ext.owl -o file://`pwd`/tmp.owl
rm tmp.obo # Cleaning up
echo ''
echo "*** Generating release files using the $REASONER reasoner ***"
echo ''
ontology-release-runner --reasoner $REASONER tmp.owl  --no-subsets --simple --relaxed --asserted --allow-overwrite --outdir oort
rm tmp.owl # Cleaning up
echo ''
echo "*** Generating obograph JSON version***"
owltools oort/fbbt.owl -o -f json oort/fbbt.json
echo ''
echo "*** Filtering relations to generating basic & FB versions ***"
owltools oort/fbbt-simple.obo --make-subset-by-properties part_of develops_from // -o file://`pwd`/oort/fbbt-basic.owl
export FB_REL_WL="connected_to develops_directly_from develops_from electrically_synapsed_to fasciculates_with has_part has_postsynaptic_terminals_in has_presynaptic_terminals_in has_soma_location has_synaptic_terminals_in has_synaptic_terminals_of innervated_by innervates overlaps part_of partially_overlaps synapsed_by synapsed_to synapsed_via_type_III_bouton_to synapsed_via_type_II_bouton_to synapsed_via_type_Ib_bouton_to synapsed_via_type_Is_bouton_to //"
obolib-owl2obo oort/fbbt-basic.owl -o oort/fbbt-basic.obo 
rm oort/fbbt-basic.owl  # Cleaning up.  No point in keeping OWL version
owltools oort/fbbt-simple.obo --make-subset-by-properties $FB_REL_WL -o file://`pwd`/tmp.owl
obolib-owl2obo tmp.owl -o oort/fbbt-flybase.obo
cat tmp.obo | sed 's/^xref: OBO_REL:part_of/xref_analog: OBO_REL:part_of/' | sed 's/^xref: OBO_REL:has_part/xref_analog: OBO_REL:has_part/' > oort/fbbt-flybase.obo  # Perhaps just make a generic substitution for xref: OBO_REL ?
rm tmp.owl  # Cleaning up
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
