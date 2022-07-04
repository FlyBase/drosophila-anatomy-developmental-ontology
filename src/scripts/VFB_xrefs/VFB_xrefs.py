#!/usr/bin/env python3

"""
Makes a template for adding VFB xrefs to classes that are is_a or part_of descendants of 'nervous system' or 'sense organ'.
"""

import requests
import json
import pandas as pd
from collections import OrderedDict

fbbt = json.load(open("../../fbbt.json", "r"))

# exclusions
new_cells = pd.read_csv(("../patterns/robot_template_projects"
						"/hemibrain_new_types/new_cell_types.tsv"), sep='\t')
new_cells['FBbt_id_long'] = new_cells['FBbt_id'].apply(
						lambda x: 'http://purl.obolibrary.org/obo/' + x.replace(':','_'))
new_ALLNs = pd.read_csv(("../patterns/robot_template_projects"
						"/hemibrain_new_types/new_ALLNs.tsv"), sep='\t')
new_ALLNs['FBbt_id_long'] = new_ALLNs['FBbt_id'].apply(
						lambda x: 'http://purl.obolibrary.org/obo/' + x.replace(':','_'))
feng_ids = ['http://purl.obolibrary.org/obo/FBbt_000' + n for n in [str(i) for i in range(51089, 51173)]]

excluded_terms = new_cells['FBbt_id_long'].tolist() + new_ALLNs['FBbt_id_long'].tolist() + feng_ids

#find all nervous systems and parts of them - nervous system = FBbt_00005093

terms = ['http://purl.obolibrary.org/obo/FBbt_00005093', 'http://purl.obolibrary.org/obo/FBbt_00005155']
result = ['http://purl.obolibrary.org/obo/FBbt_00005093', 'http://purl.obolibrary.org/obo/FBbt_00005155']
x = 1
while x > 0:
    x = 0
    new_terms = list()
    for e in fbbt['graphs'][0]['edges']:
        if (e['obj'] in terms) and ((e['pred'] == 'http://purl.obolibrary.org/obo/BFO_0000050') \
                                     or (e['pred'] == 'is_a')):
            new_terms.append(e['sub'])
            x += 1
    terms.clear()
    for i in new_terms:
        if i not in result:
            result.append(i)
            terms.append(i)
    new_terms.clear()

# remove excluded cell types

result = [r for r in result if r not in excluded_terms]

"""
# to output list of results - not usually needed

result_df = pd.DataFrame(result)
result_df.to_csv("./result_list.tsv", sep = "\t", header=False, index=False)
"""

#generate VFB refs
VFB_dict = OrderedDict([])
for i in result:
    fb_id = i.split("/")[-1]
    VFB_dict[i] = "VFB:" + fb_id

# Make a dictionary with key - column header & value = template specification (first row of table).
# Make first two columns

template_seed = OrderedDict([ ('ID' , 'ID'), ("Xref" , "A oboInOwl:hasDbXref")])

# Create dataFrame for template
# from_records takes a list of dicts - one for each row.  We only have one row.

template = pd.DataFrame.from_records([template_seed])

for i in VFB_dict:

    row_od = OrderedDict([]) #new template row as an empty ordered dictionary
    for c in template.columns: #make columns and blank data for new template row
        row_od.update([(c , "")])

    #ID and xref
    row_od['ID'] = i
    row_od["Xref"] = VFB_dict[i]

    #make new row into a DataFrame and add it to template
    new_row = pd.DataFrame.from_records([row_od])
    template = pd.concat([template, new_row], ignore_index=True, sort=False)

template.to_csv("./VFB_template.tsv", sep = "\t", header=True, index=False)
