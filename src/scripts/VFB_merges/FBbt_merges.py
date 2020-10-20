# Maps a list of FBbt IDs (obsolete and in use in VFB) to their 'term replaced by' FBbt IDs and produces cypher commands to transfer annotations in VFB to the replacement terms.

import json
import re

# open list of obsolete terms in use

with open("obsolete_terms.txt", "r") as f:
	input_list = f.read().splitlines()

# remove empty strings
input_list = [i for i in input_list if i]


# get FBbt ids from list in format http://purl.obolibrary.org/obo/FBbt_00000000


def change_iri_type(input_list, id_type='full'):
	"""
	Finds an FBbt ID of any format in each entry of a list and produces a list of IRIs, default is full-length.
	
	id_type can be 'full' (default), 'colon' - e.g. FBbt:00000001 or 'underscore' - e.g. FBbt_00000001.
	Should be 1 FBbt ID per list item.
	"""
	iri_list = []
	pattern = re.compile("FBbt[_:]([0-9]+)")
	for x in input_list:
		m = re.search(pattern, x)
		if m:
			if id_type == 'full':
				iri_list.append("http://purl.obolibrary.org/obo/FBbt_" + m.group(1))
			if id_type == 'colon':
				iri_list.append("FBbt:" + m.group(1))
			if id_type == 'underscore':
				iri_list.append("FBbt_" + m.group(1))
		else:
			raise ValueError("No FBbt ID in entry: " + str(x))
	return iri_list


ob_term_ids = change_iri_type(input_list)


# load fbbt.json and map obsolete IDs to new IDs (using IAO_0100001 'term replaced by' annotation)

fbbt = json.load(open("fbbt.json", "r"))

mapping_dict = {}
failed_mappings = []

for i in ob_term_ids:
	for n in fbbt['graphs'][0]['nodes']:
		if n['id'] == i:
			for p in n['meta']['basicPropertyValues']:
				if p['pred'] == "http://purl.obolibrary.org/obo/IAO_0100001":
					mapping_dict[change_iri_type([i], 'underscore')[0]] = change_iri_type([p['val']], 'underscore')[0]


# write 2 cypher commands for merging for each obsoleted term into a file

def command_writer(old_id, new_id):

	command_1 = ("MATCH (c:Class {short_form: '%s'})<-[r:Related]-(i:Individual), (c2:Class {short_form: '%s'}) MERGE (c2)<-[r2:Related]-(i) SET r2=properties(r) DELETE r") %(old_id, new_id)

	command_2 = ("MATCH (c:Class {short_form: '%s'})<-[r:INSTANCEOF]-(i:Individual), (c2:Class {short_form: '%s'}) MERGE (c2)<-[r2:r:INSTANCEOF]-(i) SET r2=properties(r) DELETE r") %(old_id, new_id)

	return command_1, command_2

ob_term_ids = change_iri_type(ob_term_ids, 'underscore')


n = 0
for i in ob_term_ids:
	try:
		x = command_writer(i, mapping_dict[i])
	except KeyError:
		failed_mappings.append(i)
		continue

	if n == 0:
		with open("cypher.txt", "w") as f:
			f.write(x[0] + '\n' + x[1] + '\n')	
	if n > 0:
		with open("cypher.txt", "a") as f:
			f.write(x[0] + '\n' + x[1] + '\n')
	n += 1

if len(failed_mappings) > 0:
	print("Warning: Some terms could not be mapped using term_replaced_by:")
	print(failed_mappings)
else:
	print("All terms mapped successfully")


