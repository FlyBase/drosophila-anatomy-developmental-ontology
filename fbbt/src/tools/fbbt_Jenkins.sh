echo ''
echo '*** Checking -edit file ***'
echo ''
chado_load_checks.pl fbbt/src/ontology/fbbt-edit.obo > fbbt-edit_checks.txt
echo ''
echo '*** Generating potential release ***'
echo ''
echo '*** Merging source files & imports ***'
echo ''
owltools --catalog-xml fbbt/src/ontology/catalog-v001.xml fbbt/src/ontology/fbbt-edit.obo --merge-import-closure --output -f obo tmp.obo

echo '** Rolling autodefs **'
update_EC_defs.pl tmp.obo > tmp2.obo
echo ''

echo '*** Merging accessory files ***'
owltools fbbt/src/ontology/fbbt_auth_attrib_licence.owl --merge tmp2.obo -o -f obo tmp3.obo

# Fix namespace issues caused by merge:

cat tmp3.obo | perl -p -e  's/namespace: fly_anatomy.ontology\n//' | perl -p -e 's/^ontology: fbbt$/ontology: fbbt\ndefault-namespace: fly_anatomy.ontology/' > tmp4.obo


echo ''
echo '*** Setting version iri ***'

if  [$RELEASE == ''];
    then export RELEASE=`date "+%Y-%m-%d"`; echo 'No $RELEASE specified, setting automatically to '$RELEASE
fi

owltools tmp4.obo --set-ontology-id -v 'http://purl.obolibrary.org/obo/fbbt/'$RELEASE'/fbbt.owl' 'http://purl.obolibrary.org/obo/fbbt.owl' -o tmp.owl


#rm tmp.obo
#rm tmp2.obo # Cleaning up

echo ''
echo "*** Generating release files using the $REASONER reasoner ***"
echo ''
ontology-release-runner --reasoner elk tmp.owl  --no-subsets --simple --relaxed --asserted --allow-overwrite --outdir oort

# rm tmp3.obo # Cleaning up
echo ''
echo "*** Generating obograph JSON version***"
owltools oort/fbbt.owl -o -f json oort/fbbt.json
echo ''
echo "*** Filtering relations to generating basic & FB versions ***"
owltools oort/fbbt-simple.obo --make-subset-by-properties part_of develops_from // -o -f obo oort/fbbt-basic.obo  # Basic avoids properties that might => cycles

export FB_REL_WL="connected_to develops_directly_from develops_from electrically_synapsed_to fasciculates_with has_part has_postsynaptic_terminals_in has_presynaptic_terminals_in has_soma_location has_synaptic_terminals_in has_synaptic_terminals_of innervated_by innervates overlaps part_of partially_overlaps synapsed_by synapsed_by_type_III_bouton_of synapsed_by_type_II_bouton_of synapsed_by_type_Ib_bouton_of synapsed_by_type_Is_bouton_of releases_neurotransmitter secretes_hormone located_in inheres_in has_quality has_function_in_part_of has_function_in expresses contained_in composed_primarily_of capable_of_part_of capable_of synapsed_to synapsed_via_type_III_bouton_to synapsed_via_type_II_bouton_to synapsed_via_type_Ib_bouton_to synapsed_via_type_Is_bouton_to tracheates //"

owltools oort/fbbt-simple.obo --make-subset-by-properties $FB_REL_WL -o -f obo tmp6.obo

echo ''
echo '***Building FlyBase version***'
echo ''
robot remove --input tmp6.obo\
--select "owl:deprecated='true'^^xsd:boolean" --trim true --output tmp6-no-obsoletes.obo
robot remove --input tmp6.obo\
--select object-properties --trim true --output tmp6-all-classes.obo
robot merge --collapse-import-closure false --input tmp6-all-classes.obo\
--input tmp6-no-obsoletes.obo --output tmp7.obo
rm tmp6-all-classes.obo tmp6-no-obsoletes #cleanup
cat tmp7.obo | sed 's/^xref: OBO_REL:part_of/xref_analog: OBO_REL:part_of/' | sed 's/^xref: OBO_REL:has_part/xref_analog: OBO_REL:has_part/' | egrep -v "^property_value: .+$" | egrep -v "^owl-axioms: .+$" | sed s'/^default-namespace: fly_anatomy.ontology/default-namespace: FlyBase anatomy CV/' | egrep -v "^expand_expression_to: .+$" > oort/fly_anatomy.obo  # Perhaps just make a generic substitution for xref: OBO_REL ?
#rm tmp.owl  # Cleaning up
#rm tmp2.obo # Cleaning up
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
