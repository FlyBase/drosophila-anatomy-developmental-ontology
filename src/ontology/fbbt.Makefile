## Customize Makefile settings for fbbt
## 
## If you need to customize your Makefile, make
## changes here rather than in the main Makefile

tmp/fbbt-obj.obo: fbbt-simple.obo
	$(ROBOT) remove -i $< --select object-properties --trim true -o $@.tmp.obo && grep -v ^owl-axioms $@.tmp.obo > $@ && rm $@.tmp.obo

ASSETS := $(ASSETS) fly-anatomy.obo

	# Perhaps replace last step with a generic substitution for xref: OBO_REL ?
fly-anatomy.obo: #fbbt-simple.obo tmp/fbbt-obj.obo rem_flybase.txt
	cat fbbt-simple.obo | perl -0777 -e '$$_ = <>; s/name[:].*?\nname[:]/name:/g; print' | perl -0777 -e '$$_ = <>; s/def[:].*?\ndef[:]/def:/g; print' > tmp/fbbt-simple-stripped.obo &&\
	$(ROBOT) remove -vv -i tmp/fbbt-simple-stripped.obo --select "owl:deprecated='true'^^xsd:boolean" --trim true \
		merge --collapse-import-closure false --input tmp/fbbt-obj.obo -o $@.tmp.obo
		#remove --term-file rem_flybase.txt --trim false 
	cat $@.tmp.obo | sed 's/^xref: OBO_REL:part_of/xref_analog: OBO_REL:part_of/' | sed 's/^xref: OBO_REL:has_part/xref_analog: OBO_REL:has_part/' | grep -v property_value: | grep -v ^owl-axioms | sed s'/^default-namespace: fly_anatomy.ontology/default-namespace: FlyBase anatomy CV/' | grep -v ^expand_expression_to > $@  && rm $@.tmp.obo
