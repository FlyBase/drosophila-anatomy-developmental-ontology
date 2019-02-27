Mappings for each category from larvalbrain.org are in spreadsheets/fb_lb_<category>_mapping.csv. These have been manually checked, terms that match completely have "y" in first column, terms that are approximate matches have "a" (e.g. if FBbt does not have a larval-specific term) and no match is "n".

To edit the mapped terms in fbbt:
1. Edit appropriate fb_lb_<category>_mapping.csv
2. Generate new <category>_template.tsv files using fb_lb_template_gen notebook
3. Generate larvalbrain_<category>.owl file using ROBOT (change category as appropriate):

robot template --input-iri http://purl.obolibrary.org/obo/ro.owl --template fascicle_template.tsv \
annotate --ontology-iri http://purl.obolibrary.org/obo/fbbt/imports/larvalbrain_fascicles.owl  --output larvalbrain_fascicles.owl

4. Replace larvalbrain_<category>.owl file in /imports folder


Other info:
extraction_of_larvalbrain_terms.ipynb gets terms from larvalbrain.org and saves these to spreadsheets/lb_<category>.tsv

mapping_table_generator.ipynb attempts to auto-match larvalbrain terms from spreadsheets/lb_<category>.tsv to fbbt terms and makes a file spreadsheets/<category>_candidates.tsv'. This must be manually checked to find the correct terms.


#to do:
way of checking for changes to larvalbrain terms
way of checking for obsoletion of FBbt terms
add lineage tracts to ontology to be mapped
