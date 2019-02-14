Mappings for each category from larvalbrain.org are in spreadsheets/fb_lb_<category>_mapping.csv. These have been manually checked, terms that match completely have "y" in first column, terms that are approximate matches have "a" (e.g. if FBbt does not have a larval-specific term) and no match is "n".

To edit the mapped terms in fbbt-edit:
1. *Remove old xrefs somehow?
2. Edit appropriate fb_lb_<category>_mapping.csv
3. Generate new <category>_template.tsv files using fb_lb_template_gen notebook
4. Generate and merge in terms


extraction_of_larvalbrain_terms.ipynb gets terms from larvalbrain.org and saves these to spreadsheets/lb_<category>.tsv

mapping_table_generator.ipynb attempts to auto-match larvalbrain terms from spreadsheets/lb_<category>.tsv to fbbt terms and makes a file spreadsheets/<category>_candidates.tsv'. This must be manually checked to find the correct terms.


#to do:
way of removing old xrefs - unmerge strips all annotations(!), so not suitable...
way of checking for changes to larvalbrain terms
way of checking for obsoletion of FBbt terms
add lineage tracts to ontology to be mapped
