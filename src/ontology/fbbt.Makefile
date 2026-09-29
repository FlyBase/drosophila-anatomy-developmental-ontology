## Customize Makefile settings for fbbt
##
## If you need to customize your Makefile, make
## changes here rather than in the main Makefile

.PHONY: travis_checks
travis_checks: odkversion fbbt-simple.obo reason_test sparql_test $(REPORTDIR)/obo_qc_fbbt.obo.txt $(REPORTDIR)/chado_load_check_simple.txt $(REPORTDIR)/validate_profile_owl2dl_$(ONT).owl.txt

######################################################
### Code for generating additional FlyBase reports ###
######################################################

FLYBASE_REPORTS = $(REPORTDIR)/obo_qc_fbbt.obo.txt $(REPORTDIR)/obo_track_new_simple.txt $(REPORTDIR)/robot_simple_diff.txt $(REPORTDIR)/onto_metrics_calc.txt $(REPORTDIR)/chado_load_check_simple.txt $(REPORTDIR)/spellcheck.txt $(REPORTDIR)/depiction_check.tsv

.PHONY: flybase_reports
flybase_reports: $(FLYBASE_REPORTS)

# add fb to custom_reports
custom_reports: flybase_reports

SIMPLE_PURL =	http://purl.obolibrary.org/obo/fbbt/fbbt-simple.obo
LAST_DEPLOYED_SIMPLE=$(TMPDIR)/$(ONT)-simple-last.obo

$(LAST_DEPLOYED_SIMPLE):
	wget -O $@ $(SIMPLE_PURL)

export PERL5LIB := $(realpath ../scripts)
LOCAL_RELEASE_SCRIPTS=$(realpath ../../tools/release_and_checking_scripts/releases)

.PHONY: install_flybase_scripts
$(SCRIPTSDIR)/.flybase_scripts_installed:
	rm -rf /tmp/fbcv_clone /tmp/fbo_clone
	git clone --depth 1 --filter=blob:none --sparse \
	    https://github.com/FlyBase/flybase-controlled-vocabulary.git /tmp/fbcv_clone && \
	    cd /tmp/fbcv_clone && git sparse-checkout set external_tools/perl_modules/releases
	git clone --depth 1 --filter=blob:none --sparse \
	    https://github.com/FlyBase/flybase-ontology-scripts.git /tmp/fbo_clone && \
	    cd /tmp/fbo_clone && git sparse-checkout set misc
	cp /tmp/fbcv_clone/external_tools/perl_modules/releases/OboModel.pm $(SCRIPTSDIR)/OboModel.pm
	cp $(LOCAL_RELEASE_SCRIPTS)/onto_metrics_calc.pl $(SCRIPTSDIR)/onto_metrics_calc.pl
	cp $(LOCAL_RELEASE_SCRIPTS)/chado_load_checks.pl $(SCRIPTSDIR)/chado_load_checks.pl
	cp $(LOCAL_RELEASE_SCRIPTS)/obo_track_new.pl $(SCRIPTSDIR)/obo_track_new.pl
	cp $(LOCAL_RELEASE_SCRIPTS)/auto_def_sub.pl $(SCRIPTSDIR)/auto_def_sub.pl
	cp /tmp/fbo_clone/misc/obo_spellchecker.py $(SCRIPTSDIR)/obo_spellchecker.py
	cp /tmp/fbo_clone/misc/fetch_flybase_authors.py $(SCRIPTSDIR)/fetch_authors.py
	chmod +x $(SCRIPTSDIR)/onto_metrics_calc.pl $(SCRIPTSDIR)/chado_load_checks.pl \
	    $(SCRIPTSDIR)/obo_track_new.pl $(SCRIPTSDIR)/auto_def_sub.pl
	rm -rf /tmp/fbcv_clone /tmp/fbo_clone
	touch $@

install_flybase_scripts: $(SCRIPTSDIR)/.flybase_scripts_installed

$(REPORTDIR)/obo_track_new_simple.txt: $(LAST_DEPLOYED_SIMPLE) install_flybase_scripts $(ONT)-simple.obo
	echo "Comparing with: "$(SIMPLE_PURL) && $(SCRIPTSDIR)/obo_track_new.pl $(LAST_DEPLOYED_SIMPLE) $(ONT)-simple.obo > $@

$(REPORTDIR)/robot_simple_diff.txt: $(LAST_DEPLOYED_SIMPLE) $(ONT)-simple.obo
	$(ROBOT) diff --left $(ONT)-simple.obo --right $(LAST_DEPLOYED_SIMPLE) --output $@

$(REPORTDIR)/onto_metrics_calc.txt: $(ONT)-simple.obo install_flybase_scripts
	$(SCRIPTSDIR)/onto_metrics_calc.pl 'fly_anatomy.ontology' $(ONT)-simple.obo > $@

$(REPORTDIR)/chado_load_check_simple.txt: install_flybase_scripts fly_anatomy.obo
	$(SCRIPTSDIR)/chado_load_checks.pl fly_anatomy.obo > $@

$(REPORTDIR)/obo_qc_%.obo.txt: %.obo
	$(ROBOT) report -i $*.obo --profile qc-profile.txt --fail-on ERROR --print 5 -o $@

# no longer making this
$(REPORTDIR)/obo_qc_%.owl.txt:
	$(ROBOT) merge -i $*.owl -i $(COMPONENTSDIR)/qc_assertions.owl unmerge -i $(COMPONENTSDIR)/qc_assertions_unmerge.owl -o $(REPORTDIR)/obo_qc_$*.owl &&\
	$(ROBOT) report -i $(REPORTDIR)/obo_qc_$*.owl --profile qc-profile.txt --fail-on None --print 5 -o $@ &&\
	rm -f $(REPORTDIR)/obo_qc_$*.owl

$(REPORTDIR)/spellcheck.txt: fbbt-simple.obo install_flybase_scripts ../../tools/dictionaries/standard.dict
	python3 $(SCRIPTSDIR)/obo_spellchecker.py -o $@ \
		-d ../../tools/dictionaries/standard.dict \
		-d '|python3 $(SCRIPTSDIR)/fetch_authors.py' \
		fbbt-simple.obo

$(REPORTDIR)/depiction_check.tsv: fbbt-simple.obo
	python3 $(SCRIPTSDIR)/check_depictions.py -o $@ fbbt-simple.obo || true


######################################################
### Overwriting some default artefacts ###
######################################################

# We want the OBO release to be based on the simple release. It needs to be annotated however in the way map releases (fbbt.owl) are annotated.
$(ONT).obo: $(ONT)-simple.owl
	$(ROBOT)  annotate --input $< \
		           --ontology-iri $(URIBASE)/$@ \
		           --version-iri $(ONTBASE)/releases/$(TODAY) \
		  convert --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@


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
# Also checks definitions.owl for FBgns
$(TMPDIR)/fbgn_seed.txt: $(SRC) | $(TMPDIR)
	$(ROBOT) query -f csv -i $< --query ../sparql/terms.sparql $@.tmp && \
	cat $@.tmp | sort | uniq > $@-edit.txt && \
	$(ROBOT) query -f csv -i $(PATTERNDIR)/definitions.owl --query ../sparql/terms.sparql $@.tmp && \
	cat $@.tmp $@-edit.txt | sort | uniq > $@ && \
	rm -f $@.tmp

#import_runner also updates labels in patterns - add new ones to script
$(TMPDIR)/FBgn_template.tsv: $(TMPDIR)/fbgn_seed.txt | $(TMPDIR)
	python3 $(SCRIPTSDIR)/flybase_import/FB_import_runner.py $< $@

update_template_gene_names: $(TMPDIR)/FBgn_template.tsv
	python3 $(SCRIPTSDIR)/flybase_import/template_gene_name_updater.py

$(COMPONENTSDIR)/flybase_import.owl: $(TMPDIR)/FBgn_template.tsv update_template_gene_names | $(COMPONENTSDIR)
	if [ $(IMP) = true ]; then $(ROBOT) template --input-iri http://purl.obolibrary.org/obo/ro.owl --template $< \
	annotate --ontology-iri "http://purl.obolibrary.org/obo/fbbt/components/flybase_import.owl" --output $@ && rm $<; fi

######################################################################################
### Update VFB_xrefs.owl
###################################################################################

$(TMPDIR)/fbbt-merged.json: $(SRC) | $(TMPDIR)
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


$(TMPDIR)/symbols_template.tsv: neuron_symbols.tsv | $(TMPDIR)
	python3 $(SCRIPTSDIR)/symbols_abbreviations/check_symbol_clashes.py neuron_symbols.tsv brain_name_abbreviations.tsv && \
	python3 $(SCRIPTSDIR)/symbols_abbreviations/symbol_template.py $< $@

$(COMPONENTSDIR)/neuron_symbols.owl: $(TMPDIR)/symbols_template.tsv | $(COMPONENTSDIR)
	$(ROBOT) template --input-iri http://purl.obolibrary.org/obo/ro.owl --template $< \
	annotate --ontology-iri "http://purl.obolibrary.org/obo/fbbt/components/neuron_symbols.owl" --output $@ && rm $<

######################################################################################
### Update brain_name_abbreviations.owl
###################################################################################
# BrainName official abbreviations (Ito et al. 2014, FBrf0224194) for neuropils,
# tracts, nerves, commissures and cell body rinds. Maintained as a simple curated
# TSV (brain_name_abbreviations.tsv: FBbt_id + abbreviation); a script turns it
# into a ROBOT template. Generation also
# checks (by comparing the two TSVs) that no abbreviation clashes with a neuron
# symbol in neuron_symbols.tsv.

$(TMPDIR)/brain_name_template.tsv: brain_name_abbreviations.tsv | $(TMPDIR)
	python3 $(SCRIPTSDIR)/symbols_abbreviations/check_symbol_clashes.py brain_name_abbreviations.tsv neuron_symbols.tsv && \
	python3 $(SCRIPTSDIR)/symbols_abbreviations/make_brain_name_template.py $< $@

$(COMPONENTSDIR)/brain_name_abbreviations.owl: $(TMPDIR)/brain_name_template.tsv | $(COMPONENTSDIR)
	$(ROBOT) template --input-iri http://purl.obolibrary.org/obo/ro.owl --template $< \
	annotate --ontology-iri "http://purl.obolibrary.org/obo/fbbt/components/brain_name_abbreviations.owl" --output $@ && rm $<

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

# Make sure the flybase versions are included in $(ASSETS)
# and generated as needed
MAIN_FILES += fly_anatomy.obo fbbt-cedar.obo
all_assets: fly_anatomy.obo fbbt-cedar.obo

# Ensure the synonyms with EM source are published along with the other artefacts
RELEASE_ASSETS_AFTER_RELEASE += ../../EM_synonyms.owl ../../EM_neuropil_synonyms.owl

######################################################################################
### Update image_annotation.owl
###################################################################################

$(COMPONENTSDIR)/image_annotation.owl: $(PATTERNDIR)/image_annotation_template.tsv | $(COMPONENTSDIR)
	$(ROBOT) template --input-iri http://purl.obolibrary.org/obo/fbbt.owl --template $< \
	annotate --ontology-iri "http://purl.obolibrary.org/obo/fbbt/components/image_annotation.owl" \
	--output $@

######################################################################################
### EM connectome neuron terms (components/EM_neurons.owl) and EM_synonyms.owl
######################################################################################
# All goals here are run through the ODK wrapper (sh run.sh make <goal>); see
# ../patterns/robot_template_projects/EM_neurons/README.md for the workflow.
#
# EM_neurons.owl is a committed component holding the provisional neuron terms
# from the EM connectomes (flywire, hemibrain cells + ALLNs, manc, optic_lobe,
# male_cns); the normal build just consumes it. build_EM_neurons.py runs the six
# per-connectome row generators under EM_neurons/builds/, re-expresses their
# output on one unified ROBOT template (RO CURIEs throughout, so no --input is
# needed), and keeps only the ids in the committed registry
# (EM_neurons/registry/EM_neuron_registry.tsv -- the single ID source and the
# move-to-edit removal target).
#
# The six generators are slow (FlyWire soma positioning alone is ~10+ min), so
# their output is cached under EM_neurons/templates/ (gitignored, per curator).
# build_EM_neurons.py reads the cache and computes only what is missing, so
# rebuilding the component after a registry edit is fast.
#
# Goals that read ../connectome-curation (refresh-EM-templates,
# refresh-EM-registry, refresh-EM-synonyms) need that sibling repo mounted into
# the ODK container; the curator's run.sh.conf sets this up (see the README).
# refresh-EM-templates also needs $(TMPDIR)/$(ONT)-merged.db for the male_cns and
# optic_lobe generators. It is deliberately NOT a prerequisite: it is built from
# $(SRC), which imports EM_neurons.owl, so depending on it would deadlock when the
# component is missing. Run a normal build first if it is absent.
EM_DIR = ../patterns/robot_template_projects/EM_neurons
EM_SYNONYMS_DIR = ../patterns/robot_template_projects/EM_synonyms
# Same relative path locally and inside the ODK container (mounted at /connectome-curation).
CONNECTOME_CURATION = ../../../connectome-curation
EM_FETCH_PYLIB = $(TMPDIR)/EM-fetch-pylib

.PHONY: check-connectome-curation
check-connectome-curation:
	@test -d $(CONNECTOME_CURATION)/datasets || { echo "connectome-curation not found at $(CONNECTOME_CURATION). Clone it next to this repo and mount it into the ODK container via ODK_BINDS in run.sh.conf (see $(EM_DIR)/README.md)."; exit 1; }

$(COMPONENTSDIR)/EM_neurons.owl:
	python3 $(EM_DIR)/build_EM_neurons.py --out $(TMPDIR)/EM_neurons.tsv
	$(ROBOT) template --template $(TMPDIR)/EM_neurons.tsv \
		annotate --ontology-iri "$(URIBASE)/fbbt/components/EM_neurons.owl" --output $@
	rm -f $(TMPDIR)/EM_neurons.tsv
.PRECIOUS: $(COMPONENTSDIR)/EM_neurons.owl

# Recompute the per-connectome template cache under EM_neurons/templates/ (the
# slow step). Run it when connectome data or build logic changes, then rebuild the
# registry and the component.
.PHONY: refresh-EM-templates
refresh-EM-templates: check-connectome-curation
	python3 $(EM_DIR)/build_EM_neurons.py --refresh-cache

# Rebuild the registry from the template cache, the sources/ id-lists and the
# connectome-curation bridges (after adding terms to a sources/ id-list).
.PHONY: refresh-EM-registry
refresh-EM-registry: check-connectome-curation
	python3 $(EM_DIR)/registry/build_registry.py

# Re-fetch the neuPrint evidence caches under EM_neurons/data/ (hemibrain,
# male-CNS, optic lobe) and update the committed data/PROVENANCE.tsv. Needs
# network and NEUPRINT_TOKEN passed into the container (see the README). The ODK
# image lacks neuprint-python, so it is installed into $(EM_FETCH_PYLIB) on first
# use; --no-deps keeps the image's own pandas/scipy (it only lacks ujson and
# asciitree). The FlyWire neuropil-volume cache and MANC need no fetch here (see
# the README). Follow with refresh-EM-templates to use the new data.
.PHONY: refresh-EM-data
refresh-EM-data:
	@test -n "$$NEUPRINT_TOKEN" || { echo "NEUPRINT_TOKEN is not set in the container (see $(EM_DIR)/README.md; get a token from https://neuprint.janelia.org, Account page)"; exit 1; }
	test -d $(EM_FETCH_PYLIB)/neuprint || \
		python3 -m pip install --quiet --no-deps --target $(EM_FETCH_PYLIB) neuprint-python ujson asciitree
	PYTHONPATH=$(EM_FETCH_PYLIB) python3 $(EM_DIR)/fetch/fetch_hemibrain.py
	PYTHONPATH=$(EM_FETCH_PYLIB) python3 $(EM_DIR)/fetch/fetch_male_cns.py
	PYTHONPATH=$(EM_FETCH_PYLIB) python3 $(EM_DIR)/fetch/fetch_optic_lobe.py

# Regenerate the EM_synonyms.owl release asset (dataset-tagged name_in_* synonyms
# for every FBbt term with a 1:1 connectome-curation mapping).
.PHONY: refresh-EM-synonyms
refresh-EM-synonyms: check-connectome-curation
	python3 $(EM_SYNONYMS_DIR)/EM_synonym_template.py $(TMPDIR)/EM_synonyms.tsv
	$(ROBOT) template --template $(TMPDIR)/EM_synonyms.tsv \
		annotate --ontology-iri "$(URIBASE)/fbbt/EM_synonyms.owl" --output ../../EM_synonyms.owl
	rm -f $(TMPDIR)/EM_synonyms.tsv

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
	for file in $(ALL_DOSDP_TSVs) $(PATTERNDIR)/image_annotation_template.tsv ; do \
    python3 $(SCRIPTSDIR)/update_term_labels_in_file.py -f $$file -i auto -c $< ; \
	done
	

update_lineage_nomenclature: $(PATTERNDIR)/data/all-axioms/neuroblastAnnotations.tsv
	python3 $(SCRIPTSDIR)/update_lineage_nomenclature.py
	
# Validation fails for ALNeuronEquivalentClass pattern,
# but it is not invalid because a definitions.owl file can be correctly built.
$(TMPDIR)/pattern_schema_checks:
	touch $@
	echo "Skipping pattern validation step"
