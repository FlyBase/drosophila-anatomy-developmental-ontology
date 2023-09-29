import oaklib
import os
import fnmatch
import re

typedefs_file = "flybase_additions.obo"

# 1. Identify typedefs in -simple-obo artefact
# assume only one -simple.obo file in ontology directory
for file in os.listdir('.'):
    if fnmatch.fnmatchcase(file, '*-simple.obo'):
        ontology_file = file
        ont_name = ontology_file.split('-')[0]

ontology = oaklib.get_adapter(ontology_file)
all_typedefs = [t for t in ontology.entities(owl_type='owl:ObjectProperty')]

# 2. Read existing additions file and check what is missing (id could be 'id' or 'xref')
if os.path.isfile(typedefs_file):
    with open(typedefs_file, 'r') as file:
        flybase_additions_lines = [l for l in file.readlines()]

    existing_typedefs = [re.match('^xref:[ ](.*)', l).group(1) for l in flybase_additions_lines \
                            if re.match('^xref:[ ](.*)', l)]
    existing_typedefs += [re.match('^id:[ ](.*)', l).group(1) for l in flybase_additions_lines \
                            if re.match('^id:[ ](.*)', l)]
else:
    flybase_additions_lines = ['format-version: 1.2\n', 'ontology: %s\n' % ont_name, '\n']
    existing_typedefs = []

new_typedefs = [t for t in all_typedefs if not (t in existing_typedefs)]

# 3. Add stanzas for missing typedefs
# (keep old lines - allows giving custom ids if required by FlyBase)
for t in new_typedefs:
    flybase_additions_lines += '[Typedef]\n'
    flybase_additions_lines += 'id: %s\n' % ontology.label(t).replace(' ', '_')
    flybase_additions_lines += 'xref: %s\n' % t
    flybase_additions_lines += '\n'

with open(typedefs_file, "w") as file:
    file.writelines(flybase_additions_lines)
