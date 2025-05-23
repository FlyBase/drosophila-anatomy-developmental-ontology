echo ''
echo '*** Checking -edit file ***'
echo ''
chado_load_checks.pl fbbt/src/trunk/ontologies/fbbt-edit.obo > fbbt-edit_checks.txt
echo ''
echo '*** Generating potential release ***'
echo ''
echo '** Rolling autodefs **'
update_EC_defs.pl fbbt/src/trunk/ontologies/fbbt-edit.obo > tmp.obo
echo ''
echo '*** Merging source file ***'
echo ''
owltools fbbt/src/trunk/ontologies/fbbt_auth_attrib_licence.owl --merge tmp.obo --merge fbbt/src/trunk/ontologies/fbbt-ext.owl -o file://`pwd`/tmp.owl
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
export FB_REL_WL="connected_to develops_directly_from develops_from electrically_synapsed_to fasciculates_with has_part has_postsynaptic_terminals_in has_presynaptic_terminals_in has_soma_location has_synaptic_terminals_in has_synaptic_terminals_of innervated_by innervates overlaps part_of partially_overlaps synapsed_by synapsed_by_type_III_bouton_of synapsed_by_type_II_bouton_of synapsed_by_type_Ib_bouton_of synapsed_by_type_Is_bouton_of positively_regulates regulates releases_neurotransmitter secretes_hormone located_in negatively_regulates occurs_in inheres_in has_quality has_function_in_part_of has_function_in expresses contained_in composed_primarily_of capable_of_part_of capable_of synapsed_to synapsed_via_type_III_bouton_to synapsed_via_type_II_bouton_to synapsed_via_type_Ib_bouton_to synapsed_via_type_Is_bouton_to tracheates //"
#obolib-owl2obo oort/fbbt-basic.owl -o oort/fbbt-basic.obo 
# TEMJ commented above line 20170906 because Java keeps throwing "NullPointerException" errors upon obolib use after moving from clara to flybase-vm machine. Changing to use owltools instead, which has a converter of owl to obo. May want to update in the future to use ROBOT or whatever tool becomes standard. 20170906.
owltools oort/fbbt-basic.owl -o -f obo oort/fbbt-basic.obo #TEMJ added 20170906 to replace obolib command.
rm oort/fbbt-basic.owl  # Cleaning up.  No point in keeping OWL version
owltools oort/fbbt-simple.obo --make-subset-by-properties $FB_REL_WL -o file://`pwd`/tmp.owl
#obolib-owl2obo tmp.owl -o oort/fbbt-flybase.obo
# TEMJ commented above line 20170906 for same reason as above.
echo ''
echo '***Building FlyBase version***'
echo ''
owltools tmp.owl -o -f obo tmp2.obo #TEMJ added 20170906 to replace obolib command.
cat tmp2.obo | sed 's/^xref: OBO_REL:part_of/xref_analog: OBO_REL:part_of/' | sed 's/^xref: OBO_REL:has_part/xref_analog: OBO_REL:has_part/' > oort/fly_anatomy.obo  # Perhaps just make a generic substitution for xref: OBO_REL ?
rm tmp.owl  # Cleaning up
rm tmp2.obo # Cleaning up
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
