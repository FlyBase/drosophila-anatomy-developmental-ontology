echo ''
echo '**** RUNNING CHADO LOAD CHECKS ****'
echo ''
chado_load_checks.pl ontologies/tutorial.obo > chado_load_checks_out.txt
echo '' 
echo '***** RUNNING OORT ****'
echo ''
ontology-release-runner ontologies/tutorial.obo --reasoner elk  --prefix tutorial --simple --asserted --relaxed --allow-overwrite -outdir oort

