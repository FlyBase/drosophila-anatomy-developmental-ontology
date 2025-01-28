## Customize Makefile settings for fbbt
##
## If you need to customize your Makefile, make
## changes here rather than in the main Makefile

# Using .SECONDEXPANSION to include custom FlyBase files in $(ASSETS). Also rsyncing $(IMPORTS) and $(REPORT_FILES).
.SECONDEXPANSION:
.PHONY: prepare_release
prepare_release: $$(ASSETS) $(MAPPINGDIR)/fbbt.sssom.tsv flybase_reports
	rsync -R $(RELEASE_ASSETS) $(REPORT_FILES) $(FLYBASE_REPORTS) $(IMPORT_FILES) $(RELEASEDIR) &&\
	mkdir -p $(RELEASEDIR)/patterns && cp -rf $(PATTERN_RELEASE_FILES) $(RELEASEDIR)/patterns &&\
	cp $(MAPPINGDIR)/fbbt.sssom.tsv $(RELEASEDIR)/fbbt.sssom.tsv &&\
	rm -f $(CLEANFILES)
	echo "Release files are now in $(RELEASEDIR) - now you should commit, push and make a release on your git hosting site such as GitHub or GitLab"

MAIN_FILES := $(MAIN_FILES) fly_anatomy.obo fbbt-cedar.obo
CLEANFILES := $(CLEANFILES) $(patsubst %, $(IMPORTDIR)/%_terms_combined.txt, $(IMPORTS))

######################################################
### Code for generating additional FlyBase reports ###
######################################################

FLYBASE_REPORTS = odkversion reason_test sparql_test $(REPORTDIR)/obo_qc_fbbt.obo.txt $(REPORTDIR)/obo_track_new_simple.txt $(REPORTDIR)/robot_simple_diff.txt $(REPORTDIR)/onto_metrics_calc.txt $(REPORTDIR)/chado_load_check_simple.txt $(REPORTDIR)/spellcheck.txt $(REPORTDIR)/validate_profile_owl2dl_$(ONT).owl.txt

.PHONY: flybase_reports
flybase_reports: $(FLYBASE_REPORTS)

# add fb to all_reports
.PHONY: all_reports
all_reports: flybase_reports

SIMPLE_PURL =	http://purl.obolibrary.org/obo/fbbt/fbbt-simple.obo
LAST_DEPLOYED_SIMPLE=$(TMPDIR)/$(ONT)-simple-last.obo

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
	wget -O $(SCRIPTSDIR)/OboModel.pm $(obo_model)
	wget -O $(SCRIPTSDIR)/onto_metrics_calc.pl $(onto_metrics_calc) && chmod +x $(SCRIPTSDIR)/onto_metrics_calc.pl
	wget -O $(SCRIPTSDIR)/chado_load_checks.pl $(chado_load_checks) && chmod +x $(SCRIPTSDIR)/chado_load_checks.pl
	wget -O $(SCRIPTSDIR)/obo_track_new.pl $(obo_track_new) && chmod +x $(SCRIPTSDIR)/obo_track_new.pl
	wget -O $(SCRIPTSDIR)/auto_def_sub.pl $(auto_def_sub) && chmod +x $(SCRIPTSDIR)/auto_def_sub.pl
	wget -O $(SCRIPTSDIR)/obo_spellchecker.py $(spellchecker) && chmod +x $(SCRIPTSDIR)/obo_spellchecker.py
	wget -O $(SCRIPTSDIR)/fetch_authors.py $(fetch_authors) && chmod +x $(SCRIPTSDIR)/fetch_authors.py

$(REPORTDIR)/obo_track_new_simple.txt: $(LAST_DEPLOYED_SIMPLE) install_flybase_scripts $(ONT)-simple.obo
	echo "Comparing with: "$(SIMPLE_PURL) && $(SCRIPTSDIR)/obo_track_new.pl $(LAST_DEPLOYED_SIMPLE) $(ONT)-simple.obo > $@

$(REPORTDIR)/robot_simple_diff.txt: $(LAST_DEPLOYED_SIMPLE) $(ONT)-simple.obo
	$(ROBOT) diff --left $(ONT)-simple.obo --right $(LAST_DEPLOYED_SIMPLE) --output $@

$(REPORTDIR)/onto_metrics_calc.txt: $(ONT)-simple.obo install_flybase_scripts
	$(SCRIPTSDIR)/onto_metrics_calc.pl 'fly_anatomy.ontology' $(ONT)-simple.obo > $@

$(REPORTDIR)/chado_load_check_simple.txt: install_flybase_scripts fly_anatomy.obo
	$(SCRIPTSDIR)/chado_load_checks.pl fly_anatomy.obo > $@

$(REPORTDIR)/obo_qc_%.obo.txt: $*.obo
	$(ROBOT) report -i $*.obo --profile qc-profile.txt --fail-on ERROR --print 5 -o $@

# no longer making this
$(REPORTDIR)/obo_qc_%.owl.txt:
	$(ROBOT) merge -i $*.owl -i $(COMPONENTSDIR)/qc_assertions.owl unmerge -i $(COMPONENTSDIR)/qc_assertions_unmerge.owl -o $(REPORTDIR)/obo_qc_$*.owl &&\
	$(ROBOT) report -i $(REPORTDIR)/obo_qc_$*.owl --profile qc-profile.txt --fail-on None --print 5 -o $@ &&\
	rm -f $(REPORTDIR)/obo_qc_$*.owl

$(REPORTDIR)/spellcheck.txt: fbbt-simple.obo install_flybase_scripts ../../tools/dictionaries/standard.dict
	$(SCRIPTSDIR)/obo_spellchecker.py -o $@ \
		-d ../../tools/dictionaries/standard.dict \
		-d '|$(SCRIPTSDIR)/fetch_authors.py' \
		fbbt-simple.obo


######################################################
### Overwriting some default artefacts ###
######################################################
# remove redundant overlaps rels from owl files
# should no longer be necessary if https://github.com/ontodev/robot/issues/1208 gets fixed
OWL_FILES = $(foreach n,$(RELEASE_ARTEFACTS), $(n).owl)
strip_overlaps: $(OWL_FILES)
	for file in $(OWL_FILES); do \
		$(ROBOT) query -input $$file \
		--update $(SPARQLDIR)/remove_redundant_overlaps.ru \
		--output $$file ; \
	done


# Removing excess defs, labels, comments from obo files

$(ONT)-simple.obo: $(ONT)-simple.owl strip_overlaps
	$(ROBOT) convert --input $< --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo &&\
	cat $@.tmp.obo | grep -v ^owl-axioms | grep -v 'namespace[:][ ]external' | grep -v 'namespace[:][ ]quality' > $@.tmp &&\
	cat $@.tmp | perl -0777 -e '$$_ = <>; s/(?:name[:].*\n)+name[:]/name:/g; print' | perl -0777 -e '$$_ = <>; s/(?:comment[:].*\n)+comment[:]/comment:/g; print' | perl -0777 -e '$$_ = <>; s/(?:def[:].*\n)+def[:]/def:/g; print' > $@
	rm -f $@.tmp.obo $@.tmp

# We want the OBO release to be based on the simple release. It needs to be annotated however in the way map releases (fbbt.owl) are annotated.
$(ONT).obo: $(ONT)-simple.owl strip_overlaps
	$(ROBOT)  annotate --input $< --ontology-iri $(URIBASE)/$@ --version-iri $(ONTBASE)/releases/$(TODAY) \
	convert --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo &&\
	cat $@.tmp.obo | grep -v ^owl-axioms | grep -v 'namespace[:][ ]external' | grep -v 'namespace[:][ ]quality' > $@.tmp &&\
	cat $@.tmp | perl -0777 -e '$$_ = <>; s/(?:name[:].*\n)+name[:]/name:/g; print' | perl -0777 -e '$$_ = <>; s/(?:comment[:].*\n)+comment[:]/comment:/g; print' | perl -0777 -e '$$_ = <>; s/(?:def[:].*\n)+def[:]/def:/g; print' > $@
	rm -f $@.tmp.obo $@.tmp

$(ONT)-base.obo: $(ONT)-base.owl strip_overlaps
	$(ROBOT) convert --input $< --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo &&\
	cat $@.tmp.obo | grep -v ^owl-axioms > $@.tmp &&\
	cat $@.tmp | perl -0777 -e '$$_ = <>; s/(?:name[:].*\n)+name[:]/name:/g; print' | perl -0777 -e '$$_ = <>; s/(?:comment[:].*\n)+comment[:]/comment:/g; print' | perl -0777 -e '$$_ = <>; s/(?:def[:].*\n)+def[:]/def:/g; print' > $@
	rm -f $@.tmp.obo $@.tmp

$(ONT)-non-classified.obo: $(ONT)-non-classified.owl strip_overlaps
	$(ROBOT) convert --input $< --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo &&\
	cat $@.tmp.obo | grep -v ^owl-axioms > $@.tmp &&\
	cat $@.tmp | perl -0777 -e '$$_ = <>; s/(?:name[:].*\n)+name[:]/name:/g; print' | perl -0777 -e '$$_ = <>; s/(?:comment[:].*\n)+comment[:]/comment:/g; print' | perl -0777 -e '$$_ = <>; s/(?:def[:].*\n)+def[:]/def:/g; print' > $@
	rm -f $@.tmp.obo $@.tmp

$(ONT)-full.obo: $(ONT)-full.owl strip_overlaps
	$(ROBOT) convert --input $< --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo &&\
	cat $@.tmp.obo | grep -v ^owl-axioms > $@.tmp &&\
	cat $@.tmp | perl -0777 -e '$$_ = <>; s/(?:name[:].*\n)+name[:]/name:/g; print' | perl -0777 -e '$$_ = <>; s/(?:comment[:].*\n)+comment[:]/comment:/g; print' | perl -0777 -e '$$_ = <>; s/(?:def[:].*\n)+def[:]/def:/g; print' > $@
	rm -f $@.tmp.obo $@.tmp


#####################################################################################
### Regenerate placeholder definitions         (Pre-release) pipelines            ###
#####################################################################################
# There are two types of definitions that FB ontologies use: "." (DOT-) definitions are those for which the formal
# definition is translated into a human readable definitions. "$sub_" (SUB-) definitions are those that have
# special placeholder string to substitute in definitions from external ontologies
# FBbt only uses DOT definitions - to use SUB, copy code and sparql from FBcv.

$(EDIT_PREPROCESSED): $(SRC) all_robot_plugins
	$(ROBOT) flybase:rewrite-def -i $< --dot-definitions --filter-prefix FBbt -o $@


######################################################################################
### Update flybase_import.owl
###################################################################################

# Extract the list of terms from the -edit file. We cannot use $(IMPORT_SEED) for that,
# as it can only be generated after all components have been generated, but we need
# that list to generate the flybase_import.owl component (circular dependency).
$(TMPDIR)/fbgn_seed.txt: $(SRC) | $(TMPDIR)
	$(ROBOT) query -f csv -i $< --query ../sparql/terms.sparql $@.tmp && \
		cat $@.tmp | sort | uniq > $@ && \
		rm -f $@.tmp

$(TMPDIR)/FBgn_template.tsv: $(TMPDIR)/fbgn_seed.txt | $(TMPDIR)
	if [ $(IMP) = true ]; then python3 $(SCRIPTSDIR)/flybase_import/FB_import_runner.py $< $@; fi

$(COMPONENTSDIR)/flybase_import.owl: $(TMPDIR)/FBgn_template.tsv | $(COMPONENTSDIR)
	if [ $(IMP) = true ]; then $(ROBOT) template --input-iri http://purl.obolibrary.org/obo/ro.owl --template $< \
	annotate --ontology-iri "http://purl.obolibrary.org/obo/fbbt/components/flybase_import.owl" --output $@ && rm $<; fi

######################################################################################
### Update VFB_xrefs.owl
###################################################################################

$(TMPDIR)/fbbt-merged.json:
	$(ROBOT) merge -i fbbt-edit.obo \
	relax \
	convert -f json -o $@

$(COMPONENTSDIR)/VFB_xrefs.owl: $(TMPDIR)/fbbt-merged.json
	python3 ../scripts/VFB_xrefs.py && \
	$(ROBOT) template --input-iri http://purl.obolibrary.org/obo/fbbt.owl --template $(TMPDIR)/xref_template.tsv \
	annotate --ontology-iri "http://purl.obolibrary.org/obo/fbbt/components/VFB_xrefs.owl" \
	--output $@ && \
	rm $(TMPDIR)/xref_template.tsv

######################################################################################
### Update neuron_symbols.owl
###################################################################################

OTHERCOMPONENTS := $(filter-out $(COMPONENTSDIR)/neuron_symbols.owl $(COMPONENTSDIR)/flybase_import.owl, $(OTHER_SRC))
OTHERSRCMERGED = $(TMPDIR)/nosymbolsmerged-$(SRC)

$(OTHERSRCMERGED): $(EDIT_PREPROCESSED) $(OTHERCOMPONENTS)
	$(ROBOT) remove --input $< --select imports --trim false \
		merge  $(patsubst %, -i %, $(OTHERCOMPONENTS)) -o $@

$(TMPDIR)/symbols_template.tsv: neuron_symbols.tsv $(OTHERSRCMERGED) | $(TMPDIR)
	if [ $(IMP) = true ]; then python3 $(SCRIPTSDIR)/neuron_symbols/symbol_template.py $(OTHERSRCMERGED) $< $@; fi

$(COMPONENTSDIR)/neuron_symbols.owl: $(TMPDIR)/symbols_template.tsv | $(COMPONENTSDIR)
	if [ $(IMP) = true ]; then $(ROBOT) template --input-iri http://purl.obolibrary.org/obo/ro.owl --template $< \
	annotate --ontology-iri "http://purl.obolibrary.org/obo/fbbt/components/neuron_symbols.owl" --output $@ && rm $<; fi

#######################################################################
### Update mappings_xrefs.owl
#######################################################################

MAPPING_SETS = common door larvalbrain flybrain anatomical-atlas

$(MAPPINGDIR)/fbbt.sssom.tsv: $(foreach set, $(MAPPING_SETS), $(MAPPINGDIR)/$(set).sssom.tsv)
	sssom-cli $(foreach prereq, $^, -i $(prereq)) -a -p \
		--rule 'object==UBERON:* -> assign("object_source", "http://purl.obolibrary.org/obo/uberon.owl")' \
		--rule 'object==CL:*     -> assign("object_source", "http://purl.obolibrary.org/obo/cl.owl")' \
		--rule 'object==BSPO:*   -> assign("object_source", "http://purl.obolibrary.org/obo/bspo.owl")' \
		--rule 'object==CARO:*   -> assign("object_source", "http://purl.obolibrary.org/obo/caro.owl")' \
		--rule 'object==GO:*     -> assign("object_source", "http://purl.obolibrary.org/obo/go.owl")' \
		--output $@

$(COMPONENTSDIR)/mappings_xrefs.owl: $(MAPPINGDIR)/fbbt.sssom.tsv $(SCRIPTSDIR)/sssom2xrefs.rules | all_robot_plugins
	$(ROBOT) sssom:inject --create --sssom $(MAPPINGDIR)/fbbt.sssom.tsv \
		              --ruleset $(SCRIPTSDIR)/sssom2xrefs.rules \
		 annotate --ontology-iri http://purl.obolibrary.org/obo/fbbt/components/mappings_xrefs.owl \
			  --output $@

# Ensure the mapping set is published along with the other artefacts
RELEASE_ASSETS_AFTER_RELEASE += ../../fbbt.sssom.tsv

# Also publish the synonyms with EM source
RELEASE_ASSETS_AFTER_RELEASE += ../../EM_synonyms.owl

#####################################################################################
### Generate the flybase anatomy version of FBBT
#####################################################################################

$(TMPDIR)/fbbt-obj.obo:
	$(ROBOT) remove -i fbbt-simple.obo --select object-properties --trim true -o $@.tmp.obo && grep -v ^owl-axioms $@.tmp.obo > $@ && rm $@.tmp.obo

flybase_additions.obo: fbbt-simple.obo
	python3 $(SCRIPTSDIR)/FB_typedefs.py

fly_anatomy.obo: $(TMPDIR)/fbbt-obj.obo flybase_removals.txt flybase_additions.obo
	cp fbbt-simple.obo $(TMPDIR)/fbbt-simple-stripped.obo
	$(ROBOT) remove -vv -i $(TMPDIR)/fbbt-simple-stripped.obo --select "owl:deprecated='true'^^xsd:boolean" --trim true \
		merge --collapse-import-closure false --input $(TMPDIR)/fbbt-obj.obo --input flybase_additions.obo \
		remove --term-file flybase_removals.txt --trim false \
		query --update ../sparql/force-obo.ru \
		convert -f obo --check false -o $@.tmp.obo
	cat $@.tmp.obo | sed '/./{H;$!d;} ; x ; s/\(\[Typedef\]\nid:[ ]\)\([[:alpha:]_]*\n\)\(name:[ ]\)\([[:alpha:][:punct:] ]*\n\)/\1\2\3\2/' | grep -v property_value: | grep -v ^owl-axioms | sed 's/^default-namespace: fly_anatomy.ontology/default-namespace: FlyBase anatomy CV/' | grep -v ^expand_expression_to | grep -v gci_filler | grep -v '^namespace: uberon' | grep -v '^namespace: protein' | grep -v '^namespace: chebi_ontology' | grep -v '^is_cyclic: false' | grep -v 'FlyBase_miscellaneous_CV' | sed '/^date[:]/c\date: $(OBODATE)' | sed '/^data-version[:]/c\data-version: $(TODAY)' > $@  && rm $@.tmp.obo
	$(ROBOT) convert --input $@ -f obo --output $@
	sed -i 's/^xref[:][ ]OBO_REL[:]\(.*\)/xref_analog: OBO_REL:\1/' $@

# goal to make version where all synonyms are the same type and relationships are removed
fbbt-cedar.obo:
	cat fbbt-simple.obo | grep -v 'relationship:' | grep -v 'remark:' | grep -v 'property_value: owl:versionInfo' | sed 's/synonym: \(".*"\).*\(\[.*\]\)/synonym: \1 RELATED ANYSYNONYM \2/' | sed '/synonymtypedef:/c\synonymtypedef: ANYSYNONYM "Synonym type changed to related for use in CEDAR"' | sed '/^date[:]/c\date: $(OBODATE)' > $@
	$(ROBOT) annotate --input $@ --ontology-iri $(ONTBASE)/$@ $(ANNOTATE_ONTOLOGY_VERSION) \
	--annotation rdfs:comment "This release artefact contains only the classification hierarchy (no relationships) and will not be suitable for most users." \
	convert -f obo $(OBO_FORMAT_OPTIONS) -o $@


#######################################################################
### Subsets
#######################################################################

scrnaseq-slim.owl: $(ONT)-simple.owl
	owltools --use-catalog $< --extract-ontology-subset --subset scrnaseq_slim \
		--iri $(URIBASE)/fbbt/scrnaseq-slim.owl -o $@


#######################################################################
### Patterns
#######################################################################

# all filenames for pattern tsvs
ALL_DOSDP_TSVs = $(wildcard $(PATTERNDIR)/data/*/*.tsv)

$(TMPDIR)/$(ONT)-merged.db: $(SRC)
	$(ROBOT) merge -i $< -o $(TMPDIR)/$(ONT)-merged.owl
	semsql make $@

update_pattern_labels: $(TMPDIR)/$(ONT)-merged.db
	wget -O $(SCRIPTSDIR)/update_term_labels_in_file.py https://raw.githubusercontent.com/FlyBase/flybase-ontology-scripts/master/update_term_labels_in_file/src/update_term_labels_in_file.py
	for file in $(ALL_DOSDP_TSVs) ; do \
    python3 $(SCRIPTSDIR)/update_term_labels_in_file.py -f $$file -i auto -c $< ; \
	done
	

update_lineage_nomenclature: $(PATTERNDIR)/data/all-axioms/neuroblastAnnotations.tsv
	python3 $(SCRIPTSDIR)/update_lineage_nomenclature.py
	
# Validation fails for ALNeuronEquivalentClass pattern,
# but it is not invalid because a definitions.owl file can be correctly built.
$(TMPDIR)/pattern_schema_checks:
	touch $@
	echo "Skipping pattern validation step"

.PHONY: update_repo
# don't keep adding extra imports
update_repo:
	sh $(SCRIPTSDIR)/update_repo.sh
	rm -f $(foreach n,$(IMPORTS), $(IMPORTDIR)/$(n)_import.owl)
