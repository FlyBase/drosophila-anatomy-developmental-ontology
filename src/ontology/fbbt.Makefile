## Customize Makefile settings for fbbt
## 
## If you need to customize your Makefile, make
## changes here rather than in the main Makefile


#####################################################################################
### Overwrite release goals with new targets                                      ###
#####################################################################################


ASSETS := $(ASSETS) fly-anatomy.obo
OTHER_SRC:= $(OTHER_SRC) auto_generated_definitions.owl


# The prepare release goal needs to be overwritten to accomodate for the new ASSETS
prepare_release: $(ASSETS) $(PATTERN_RELEASE_FILES)
	rsync -R $(ASSETS) $(RELEASEDIR) &&\
	mkdir -p $(RELEASEDIR)/patterns &&\
	cp $(PATTERN_RELEASE_FILES) $(RELEASEDIR)/patterns &&\
	echo "Release files are now in $(RELEASEDIR) - now you should commit, push and make a release on github"

# Simple is overwritten to strip out duplicate names and definitions.
$(ONT)-simple.obo: $(ONT)-simple.owl
	$(ROBOT) convert --input $< --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo &&\
	grep -v ^owl-axioms $@.tmp.obo > $@.tmp &&\
	cat $@.tmp | perl -0777 -e '$$_ = <>; s/name[:].*\nname[:]/name:/g; print' | perl -0777 -e '$$_ = <>; s/def[:].*\nname[:]/def:/g; print' > $@
	rm -f $@.tmp.obo $@.tmp

# We want the OBO release to be based on the simple release
$(ONT).obo: $(ONT)-simple.owl
	$(ROBOT) convert --input $< --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo && grep -v ^owl-axioms $@.tmp.obo > $@ && rm $@.tmp.obo

#non_native_classes.txt: $(SRC)
#	$(ROBOT) query --use-graphs true -f csv -i $< --query ../sparql/non-native-classes.sparql $@.tmp &&\
#	cat $@.tmp | sort | uniq >  $@
#	rm -f $@.tmp

#####################################################################################
### Generate definitions automatically                                    ###
#####################################################################################
LABEL_MAP = auto_generated_definitions_label_map.txt
	
auto_generated_definitions_seed.txt: $(SRC)
	$(ROBOT) query --use-graphs false -f csv -i $(SRC) --query ../sparql/dot-definitions.sparql $@.tmp &&\
	cat $@.tmp | sort | uniq >  $@
	rm -f $@.tmp

auto_generated_definitions.tsv: $(SRC) auto_generated_definitions_seed.txt
	$(ROBOT) merge --input $(SRC) --output tmp/merged.owl &&\
	java -jar ../../bin/eq-writer.jar tmp/merged.owl auto_generated_definitions_seed.txt flybase $@ $(LABEL_MAP)

auto_generated_definitions.owl: auto_generated_definitions.tsv
	$(ROBOT) template --template $< --prefix "iao: http://purl.obolibrary.org/obo/IAO_" --ontology-iri $(ONTBASE)/$@ --output $@

#####################################################################################
### Generate the flybase anatomy version of FBBT                                  ###
#####################################################################################

	
tmp/fbbt-obj.obo: fbbt-simple.obo
	$(ROBOT) remove -i $< --select object-properties --trim true -o $@.tmp.obo && grep -v ^owl-axioms $@.tmp.obo > $@ && rm $@.tmp.obo

# Perhaps replace last step with a generic substitution for xref: OBO_REL ?

fly-anatomy.obo: fbbt-simple.obo tmp/fbbt-obj.obo rem_flybase.txt
	cat $< | perl -0777 -e '$$_ = <>; s/name[:].*\nname[:]/name:/g; print' | perl -0777 -e '$$_ = <>; s/def[:].*\nname[:]/def:/g; print' > tmp/fbbt-simple-stripped.obo &&\
	$(ROBOT) remove -vv -i tmp/fbbt-simple-stripped.obo --select "owl:deprecated='true'^^xsd:boolean" --trim true \
		merge --collapse-import-closure false --input tmp/fbbt-obj.obo \
		remove --term-file rem_flybase.txt --trim false -o $@.tmp.obo
	cat $@.tmp.obo | sed 's/^xref: OBO_REL:part_of/xref_analog: OBO_REL:part_of/' | sed 's/^xref: OBO_REL:has_part/xref_analog: OBO_REL:has_part/' | grep -v property_value: | grep -v ^owl-axioms | sed s'/^default-namespace: fly_anatomy.ontology/default-namespace: FlyBase anatomy CV/' | grep -v ^expand_expression_to > $@  && rm $@.tmp.obo
