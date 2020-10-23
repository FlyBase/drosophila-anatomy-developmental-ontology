# Maps a list of FBbt IDs (obsolete and in use in VFB) to their 'term replaced by' FBbt IDs and produces cypher commands to transfer annotations in VFB to the replacement terms.

import json
import re

# open list of obsolete terms in use

with open("obsolete_terms.txt", "r") as f:
	ob_term_ids = f.read().splitlines()

# remove empty strings
ob_term_ids = [i for i in ob_term_ids if i]


# get FBbt ids from list in format http://purl.obolibrary.org/obo/FBbt_00000000


def convert_to_short_form(iri):
	"""
	Convert any type of id to a short form (with an underscore).
	"""
	pattern = re.compile("([A-Za-z]+)[_:]([0-9]+)$")
	m = re.search(pattern, iri)
	short_form = m.group(1) + "_" + m.group(2)
	return short_form

def command_writer(old_id, new_id):

	command_1 = ("MATCH (c:Class {iri: '%s'})<-[r:Related]-(i:Individual), (c2:Class {short_form: '%s'}) MERGE (c2)<-[r2:Related]-(i) SET r2=properties(r) DELETE r") %(old_id, new_id)

	command_2 = ("MATCH (c:Class {iri: '%s'})<-[r:INSTANCEOF]-(i:Individual), (c2:Class {short_form: '%s'}) MERGE (c2)<-[r2:r:INSTANCEOF]-(i) SET r2=properties(r) DELETE r") %(old_id, new_id)

	return command_1, command_2

# load fbbt.json and map obsolete IDs to new IDs (using IAO_0100001 'term replaced by' annotation)

fbbt = json.load(open("fbbt.json", "r"))
graph = fbbt['graphs'][0]

mapping_dict = {}
failed_mappings = []

for i in ob_term_ids:
	for n in graph['nodes']:
		if (n['id'] == i) and (n['meta']['basicPropertyValues']):
			for p in n['meta']['basicPropertyValues']:
				if p['pred'] == "http://purl.obolibrary.org/obo/IAO_0100001":
					mapping_dict[i] = convert_to_short_form(p['val'])

statements = []
for i in ob_term_ids:
	try:
		x = command_writer(i, mapping_dict[i])
		statements.extend(x)
	except KeyError:
		failed_mappings.append(convert_to_short_form(i))
		continue

		
with open("cypher.txt", "w") as f:
	for s in statements:
		f.write(s + '\n')

if len(failed_mappings) > 0:
	failed_mapping_dict = {}
	consider_all_shortids = []
	for i in failed_mappings:
		consider_all_shortids.append(i)
		for n in graph['nodes']:
			if i in n['id']:
				consider_list = [convert_to_short_form(p['val']) for p in n['meta']['basicPropertyValues'] if p['pred'] == "http://www.geneontology.org/formats/oboInOwl#consider"]
				failed_mapping_dict[convert_to_short_form(i)] = consider_list
				consider_all_shortids.extend(consider_list)


	consider_label_lookup ={}
	for i in consider_all_shortids:
		for n in graph['nodes']:
			if i in n['id']:
				try:
					consider_label_lookup[i] = n['lbl']
				except KeyError:
					consider_label_lookup[i] = "<no label>"
	
	print("Warning: Some terms could not be mapped using term_replaced_by:")
	for i in failed_mappings:
		print('  %s (%s):'%(i, consider_label_lookup[i]))
		if failed_mapping_dict[i]:
			for r in failed_mapping_dict[i]:
				print('    consider - %s (%s)'%(r, consider_label_lookup[r]))
		else:
			print('    <no suggestions>')
			
else:
	print("All terms mapped successfully")


