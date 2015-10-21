# Updating of imports from GO currently uses the default update mechanism in oort using the -simple pre-reasoned version. In future, it may be worth investigating using module extraction (see https://code.google.com/p/owltools/wiki/OortExtractingModules and a more complete version of GO).

ontology-release-runner --reasoner elk $JENKINS_HOME/workspace/FBbt_GH_Marta/fbbt/src/trunk/ontologies/fbbt-edit.obo go-simple.obo --no-subsets --allow-overwrite --outdir fbbt/src/trunk/oort  
