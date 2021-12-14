## Customize Makefile settings for fbbt
## 
## If you need to customize your Makefile, make
## changes here rather than in the main Makefile

DATE   ?= $(shell date +%Y-%m-%d)

######################################################
### Code for generating additional FlyBase reports ###
######################################################

REPORT_FILES := $(REPORT_FILES) reports/obo_track_new_simple.txt  reports/robot_simple_diff.txt reports/onto_metrics_calc.txt reports/spellcheck.txt

SIMPLE_PURL =	http://purl.obolibrary.org/obo/fbbt/fbbt-simple.obo
LAST_DEPLOYED_SIMPLE=tmp/$(ONT)-simple-last.obo

$(LAST_DEPLOYED_SIMPLE):
	wget -O $@ $(SIMPLE_PURL)

obo_model=https://raw.githubusercontent.com/FlyBase/flybase-controlled-vocabulary/master/external_tools/perl_modules/releases/OboModel.pm
flybase_script_base=https://raw.githubusercontent.com/FlyBase/drosophila-anatomy-developmental-ontology/master/tools/release_and_checking_scripts/releases/
flybase_ontology_script_base=https://raw.githubusercontent.com/FlyBase/flybase-ontology-scripts/master/
onto_metrics_calc=$(flybase_script_base)onto_metrics_calc.pl
chado_load_checks=$(flybase_script_base)chado_load_checks.pl
obo_track_new=$(flybase_script_base)obo_track_new.pl
auto_def_sub=$(flybase_script_base)auto_def_sub.pl
spellchecker=$(flybase_ontology_script_base)misc/obo_spellchecker.py
fetch_authors=$(flybase_ontology_script_base)misc/fetch_flybase_authors.py

export PERL5LIB := ${realpath ../scripts}
install_flybase_scripts:
	wget -O ../scripts/OboModel.pm $(obo_model)
	wget -O ../scripts/onto_metrics_calc.pl $(onto_metrics_calc) && chmod +x ../scripts/onto_metrics_calc.pl
	wget -O ../scripts/chado_load_checks.pl $(chado_load_checks) && chmod +x ../scripts/chado_load_checks.pl
	wget -O ../scripts/obo_track_new.pl $(obo_track_new) && chmod +x ../scripts/obo_track_new.pl
	wget -O ../scripts/auto_def_sub.pl $(auto_def_sub) && chmod +x ../scripts/auto_def_sub.pl
	wget -O ../scripts/obo_spellchecker.py $(spellchecker) && chmod +x ../scripts/obo_spellchecker.py
	wget -O ../scripts/fetch_authors.py $(fetch_authors) && chmod +x ../scripts/fetch_authors.py
	echo "Warning: Chado load checks currently exclude ISBN wellformedness checks!"

reports/obo_track_new_simple.txt: $(LAST_DEPLOYED_SIMPLE) install_flybase_scripts $(ONT)-simple.obo
	echo "Comparing with: "$(SIMPLE_PURL) && ../scripts/obo_track_new.pl $(LAST_DEPLOYED_SIMPLE) $(ONT)-simple.obo > $@

reports/robot_simple_diff.txt: $(LAST_DEPLOYED_SIMPLE) $(ONT)-simple.obo
	$(ROBOT) diff --left $(ONT)-simple.obo --right $(LAST_DEPLOYED_SIMPLE) --output $@

reports/onto_metrics_calc.txt: $(ONT)-simple.obo install_flybase_scripts
	../scripts/onto_metrics_calc.pl 'fly_anatomy.ontology' $(ONT)-simple.obo > $@
	
reports/chado_load_check_simple.txt: install_flybase_scripts fly_anatomy.obo 
	../scripts/chado_load_checks.pl fly_anatomy.obo > $@

reports/spellcheck.txt: fbbt-simple.obo install_flybase_scripts ../../tools/dictionaries/standard.dict
	apt-get update && apt-get install -y python3-psycopg2
	sed -nre 's/^# pypi-requirements: //p' ../scripts/obo_spellchecker.py ../scripts/fetch_authors.py \
		| xargs python -m pip install
	../scripts/obo_spellchecker.py -o $@ \
		-d ../../tools/dictionaries/standard.dict \
		-d '|../scripts/fetch_authors.py' \
		fbbt-simple.obo

all_reports: all_reports_onestep $(REPORT_FILES)

prepare_release: $(ASSETS) $(PATTERN_RELEASE_FILES) mappings.sssom.tsv
	rsync -R $(ASSETS) $(RELEASEDIR) &&\
	mkdir -p $(RELEASEDIR)/patterns &&\
	cp $(PATTERN_RELEASE_FILES) $(RELEASEDIR)/patterns &&\
	cp mappings.sssom.tsv $(RELEASEDIR)/fbbt-mappings.sssom.tsv &&\
	echo "Release files are now in $(RELEASEDIR) - now you should commit, push and make a release on github"


######################################################
### Overwriting some default artefacts ###
######################################################
# Removing excess defs, labels, comments from obo files

$(ONT)-simple.obo: $(ONT)-simple.owl
	$(ROBOT) convert --input $< --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo &&\
	cat $@.tmp.obo | grep -v ^owl-axioms | grep -v 'namespace[:][ ]external' | grep -v 'namespace[:][ ]quality' > $@.tmp &&\
	cat $@.tmp | perl -0777 -e '$$_ = <>; s/(?:name[:].*\n)+name[:]/name:/g; print' | perl -0777 -e '$$_ = <>; s/(?:comment[:].*\n)+comment[:]/comment:/g; print' | perl -0777 -e '$$_ = <>; s/(?:def[:].*\n)+def[:]/def:/g; print' > $@
	rm -f $@.tmp.obo $@.tmp

# We want the OBO release to be based on the simple release. It needs to be annotated however in the way map releases (fbbt.owl) are annotated.
$(ONT).obo: $(ONT)-simple.owl
	$(ROBOT)  annotate --input $< --ontology-iri $(URIBASE)/$@ --version-iri $(ONTBASE)/releases/$(TODAY) \
	convert --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo &&\
	cat $@.tmp.obo | grep -v ^owl-axioms | grep -v 'namespace[:][ ]external' | grep -v 'namespace[:][ ]quality' > $@.tmp &&\
	cat $@.tmp | perl -0777 -e '$$_ = <>; s/(?:name[:].*\n)+name[:]/name:/g; print' | perl -0777 -e '$$_ = <>; s/(?:comment[:].*\n)+comment[:]/comment:/g; print' | perl -0777 -e '$$_ = <>; s/(?:def[:].*\n)+def[:]/def:/g; print' > $@
	rm -f $@.tmp.obo $@.tmp

$(ONT)-base.obo: $(ONT)-base.owl
	$(ROBOT) convert --input $< --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo &&\
	cat $@.tmp.obo | grep -v ^owl-axioms > $@.tmp &&\
	cat $@.tmp | perl -0777 -e '$$_ = <>; s/(?:name[:].*\n)+name[:]/name:/g; print' | perl -0777 -e '$$_ = <>; s/(?:comment[:].*\n)+comment[:]/comment:/g; print' | perl -0777 -e '$$_ = <>; s/(?:def[:].*\n)+def[:]/def:/g; print' > $@
	rm -f $@.tmp.obo $@.tmp
		
$(ONT)-non-classified.obo: $(ONT)-non-classified.owl
	$(ROBOT) convert --input $< --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo &&\
	cat $@.tmp.obo | grep -v ^owl-axioms > $@.tmp &&\
	cat $@.tmp | perl -0777 -e '$$_ = <>; s/(?:name[:].*\n)+name[:]/name:/g; print' | perl -0777 -e '$$_ = <>; s/(?:comment[:].*\n)+comment[:]/comment:/g; print' | perl -0777 -e '$$_ = <>; s/(?:def[:].*\n)+def[:]/def:/g; print' > $@
	rm -f $@.tmp.obo $@.tmp

$(ONT)-full.obo: $(ONT)-full.owl
	$(ROBOT) convert --input $< --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo &&\
	cat $@.tmp.obo | grep -v ^owl-axioms > $@.tmp &&\
	cat $@.tmp | perl -0777 -e '$$_ = <>; s/(?:name[:].*\n)+name[:]/name:/g; print' | perl -0777 -e '$$_ = <>; s/(?:comment[:].*\n)+comment[:]/comment:/g; print' | perl -0777 -e '$$_ = <>; s/(?:def[:].*\n)+def[:]/def:/g; print' > $@
	rm -f $@.tmp.obo $@.tmp
	

#non_native_classes.txt: $(SRC)
#	$(ROBOT) query --use-graphs true -f csv -i $< --query ../sparql/non-native-classes.sparql $@.tmp &&\
#	cat $@.tmp | sort | uniq >  $@
#	rm -f $@.tmp


#####################################################################################
### Regenerate placeholder definitions         (Pre-release) pipelines            ###
#####################################################################################
# There are two types of definitions that FB ontologies use: "." (DOT-) definitions are those for which the formal 
# definition is translated into a human readable definitions. "$sub_" (SUB-) definitions are those that have 
# special placeholder string to substitute in definitions from external ontologies
# FBbt only uses DOT definitions - SUB currently disabled

LABEL_MAP = auto_generated_definitions_label_map.txt

tmp/auto_generated_definitions_seed_dot.txt: $(SRC)
	$(ROBOT) query --use-graphs false -f csv -i $(SRC) --query ../sparql/dot-definitions.sparql $@.tmp &&\
	cat $@.tmp | sort | uniq >  $@
	rm -f $@.tmp
	
tmp/auto_generated_definitions_seed_sub.txt: $(SRC)
	$(ROBOT) query --use-graphs false -f csv -i $(SRC) --query ../sparql/classes-with-placeholder-definitions.sparql $@.tmp &&\
	cat $@.tmp | sort | uniq >  $@
	rm -f $@.tmp

tmp/merged-source-pre.owl: $(SRC)
	$(ROBOT) merge -i $(SRC) --output $@

tmp/auto_generated_definitions_dot.owl: tmp/merged-source-pre.owl tmp/auto_generated_definitions_seed_dot.txt
	java -jar ../scripts/eq-writer.jar $< tmp/auto_generated_definitions_seed_dot.txt flybase $@ $(LABEL_MAP) add_dot_refs

tmp/auto_generated_definitions_sub.owl: tmp/merged-source-pre.owl tmp/auto_generated_definitions_seed_sub.txt
	java -jar ../scripts/eq-writer.jar $< tmp/auto_generated_definitions_seed_sub.txt sub_external $@ $(LABEL_MAP) source_xref

tmp/replaced_defs.txt:
	cat tmp/auto_generated_definitions_seed_sub.txt tmp/auto_generated_definitions_seed_dot.txt | sort | uniq > $@

tmp/remove_dot_defs.txt: tmp/auto_generated_definitions_seed_dot.txt
	cp $< $@
	echo "http://purl.obolibrary.org/obo/IAO_0000115" >> $@
	echo "http://www.geneontology.org/formats/oboInOwl#hasDbXref" >> $@

pre_release: $(ONT)-edit.obo tmp/auto_generated_definitions_dot.owl tmp/remove_dot_defs.txt # tmp/auto_generated_definitions_sub.owl
	cp $(ONT)-edit.obo tmp/$(ONT)-edit-release.obo
	$(ROBOT) query -i tmp/$(ONT)-edit-release.obo --update ../sparql/remove-dot-definitions.ru -o tmp/$(ONT)-edit-release.owl
	#commenting out sub_ removal as sub_ not used in FBbt
	#sed -i '/sub_/d' tmp/$(ONT)-edit-release.obo
	$(ROBOT) merge -i tmp/$(ONT)-edit-release.owl -i tmp/auto_generated_definitions_dot.owl --collapse-import-closure false -o $(ONT)-edit-release.ofn && mv $(ONT)-edit-release.ofn $(ONT)-edit-release.owl
	echo "Preprocessing done. Make sure that NO CHANGES TO THE EDIT FILE ARE COMMITTED!"

#t:
#	$(ROBOT) query -i tmp/$(ONT)-edit-release.obo --update ../sparql/remove-dot-definitions.ru -o tmp/$(ONT)-edit-release3.obo
#	diff tmp/$(ONT)-edit-release.obo tmp/$(ONT)-edit-release3.obo > diff.txt

######################################################################################
### Update flybase_import.owl
###
###################################################################################

.PHONY: all_imports
all_imports: $(IMPORT_FILES) components/flybase_import.owl

tmp/FBgn_template.tsv: $(IMPORTSEED)
	if [ $(IMP) = true ]; then apt-get update && apt-get install -y python3-psycopg2 && \
	python3 -m pip install -r ../scripts/flybase_import/requirements.txt && \
	python3 ../scripts/flybase_import/FB_import_runner.py $(IMPORTSEED) $@; fi
	
components/flybase_import.owl: tmp/FBgn_template.tsv
	if [ $(IMP) = true ]; then $(ROBOT) template --input-iri http://purl.obolibrary.org/obo/ro.owl --template $< \
	annotate --ontology-iri "http://purl.obolibrary.org/obo/fbbt/components/flybase_import.owl" --output $@ && rm $<; fi


#######################################################################
### Update exact_mappings.owl
#######################################################################

mappings.sssom.tsv: mappings.tsv ../scripts/mappings2sssom.awk
	sort -t'	' -k1,4 $< | awk -f ../scripts/mappings2sssom.awk > $@

tmp/exact_mapping_template.tsv: mappings.sssom.tsv
	echo 'ID	Cross-reference' > $@
	echo 'ID	A oboInOwl:hasDbXref' >> $@
	sed -n '/skos:exactMatch/p' $< | cut -f1,4 >> $@

components/exact_mappings.owl: tmp/exact_mapping_template.tsv fbbt-edit.obo
	$(ROBOT) template --input fbbt-edit.obo --template tmp/exact_mapping_template.tsv \
		--ontology-iri http://purl.obolibrary.org/obo/fbbt/components/exact_mappings.owl \
		--output components/exact_mappings.owl
	rm tmp/exact_mapping_template.tsv

######################################################################################
### Generate the flybase anatomy version of FBBT
###
#####################################################################################

tmp/fbbt-obj.obo:
	$(ROBOT) remove -i fbbt-simple.obo --select object-properties --trim true -o $@.tmp.obo && grep -v ^owl-axioms $@.tmp.obo > $@ && rm $@.tmp.obo

fly_anatomy.obo: tmp/fbbt-obj.obo rem_flybase.txt
	cp fbbt-simple.obo tmp/fbbt-simple-stripped.obo
	$(ROBOT) remove -vv -i tmp/fbbt-simple-stripped.obo --select "owl:deprecated='true'^^xsd:boolean" --trim true \
		merge --collapse-import-closure false --input tmp/fbbt-obj.obo \
		remove --term-file rem_flybase.txt --trim false \
		query --update ../sparql/force-obo.ru \
		convert -f obo --check false -o $@.tmp.obo
	cat $@.tmp.obo | sed '/./{H;$!d;} ; x ; s/\(\[Typedef\]\nid:[ ]\)\([[:lower:][:punct:]]*\n\)\(name:[ ]\)\([[:lower:][:punct:] ]*\n\)/\1\2\3\2/' | grep -v property_value: | grep -v ^owl-axioms | sed 's/^default-namespace: fly_anatomy.ontology/default-namespace: FlyBase anatomy CV/' | grep -v ^expand_expression_to | grep -v gci_filler | grep -v '^namespace: uberon' | grep -v '^namespace: protein' | grep -v '^namespace: chebi_ontology' | grep -v '^is_cyclic: false' | grep -v 'FlyBase_miscellaneous_CV' | sed '/^date[:]/c\date: $(OBODATE)' | sed '/^data-version[:]/c\data-version: $(DATE)' > $@  && rm $@.tmp.obo
	$(ROBOT) convert --input $@ -f obo --output $@
	sed -i 's/^xref[:][ ]OBO_REL[:]\(.*\)/xref_analog: OBO_REL:\1/' $@

# goal to make version where all synonyms are the same type and relationships are removed
fbbt-cedar.obo:
	cat fbbt-simple.obo | grep -v 'relationship:' | grep -v 'remark:' | grep -v 'property_value: owl:versionInfo' | sed 's/synonym: \(".*"\).*\(\[.*\]\)/synonym: \1 RELATED ANYSYNONYM \2/' | sed '/synonymtypedef:/c\synonymtypedef: ANYSYNONYM "Synonym type changed to related for use in CEDAR"' | sed '/^date[:]/c\date: $(OBODATE)' > $@
	$(ROBOT) annotate --input $@ --ontology-iri $(ONTBASE)/$@ $(ANNOTATE_ONTOLOGY_VERSION) \
	--annotation rdfs:comment "This release artefact contains only the classification hierarchy (no relationships) and will not be suitable for most users." \
	convert -f obo $(OBO_FORMAT_OPTIONS) -o $@

post_release: obo_qc fly_anatomy.obo fbbt-cedar.obo reports/chado_load_check_simple.txt
	cp fly_anatomy.obo ../..
	cp fbbt-cedar.obo ../..
	mv obo_qc_$(ONT).obo.txt reports/obo_qc_$(ONT).obo.txt
	mv obo_qc_$(ONT).owl.txt reports/obo_qc_$(ONT).owl.txt
	rm imports/*_terms_combined.txt


#######################################################################
### Subsets
#######################################################################

scrnaseq-slim.owl: $(ONT)-simple.owl
	owltools --use-catalog $< --extract-ontology-subset --subset scrnaseq_slim \
		--iri $(URIBASE)/fbbt/scrnaseq-slim.owl -o $@
	
	
########################
##    TRAVIS       #####
########################

obo_qc_%.obo:
	$(ROBOT) report -i $*.obo --profile qc-profile.txt --fail-on ERROR --print 5 -o $@.txt

# currently no failure due to owl checks
obo_qc_%.owl:
	$(ROBOT) merge -i $*.owl -i components/qc_assertions.owl unmerge -i components/qc_assertions_unmerge.owl -o $@ &&\
	$(ROBOT) report -i $@ --profile qc-profile.txt --fail-on None --print 5 -o $@.txt

obo_qc: obo_qc_$(ONT).obo obo_qc_$(ONT).owl

flybase_qc.owl: odkversion obo_qc
	$(ROBOT) merge -i $(ONT)-full.owl -i components/qc_assertions.owl -o $@

flybase_qc: flybase_qc.owl
	$(ROBOT) reason --input $< --reasoner ELK  --equivalent-classes-allowed none --output test.owl &&\
	rm test.owl &&\
	echo "Success"

