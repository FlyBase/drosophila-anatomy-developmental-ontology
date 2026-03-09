---
name: move-to-edit
description: Move EM neuron terms from robot template-generated component OWL files to the main fbbt-edit.obo editors file. Use when neuron terms identified from EM data need to be promoted from components to the manually curated ontology.
user-invocable: true
argument-hint: [FBbt_ID ...]
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Move EM Neuron Terms from Components to fbbt-edit.obo

Move one or more neuron terms from robot template-generated component OWL files to the main editors file (`src/ontology/fbbt-edit.obo`), converting from OWL XML to OBO format, and removing from the source TSV to prevent regeneration.

## Arguments

One or more FBbt IDs separated by spaces (e.g., `FBbt:20000000 FBbt:20000001`).

## Key Paths

All paths are relative to the repository root unless otherwise noted.

- Editors file: `src/ontology/fbbt-edit.obo`
- Components: `src/ontology/components/`
- Robot template projects: `src/patterns/robot_template_projects/`
- ROBOT binary: `robot` (must be on the user's PATH)

## Component to Source TSV Mapping

Each component OWL file is generated from TSV files in robot_template_projects. When removing a term from a source TSV, search ALL `.tsv` files in the relevant subdirectory for the FBbt ID, as some projects use multiple TSV files.

| Component File | Source Directory | Primary TSV File(s) | ID Column |
|---|---|---|---|
| `flywire_neurons.owl` | `flywire_neurons/` | `FBbt_ID-cell_type.tsv` | `FBbt_id` |
| `hemibrain_new_cells.owl` | `hemibrain_new_types/` | `new_cell_types.tsv` | `FBbt_id` |
| `hemibrain_new_ALLNs.owl` | `hemibrain_new_types/` | `new_ALLNs.tsv` | `FBbt_id` |
| `optic_lobe_neurons.owl` | `optic_lobe/` | `new_types.tsv` | `FBbt_id` |
| `manc_new_cells.owl` | `manc_neurons/` | `new_cell_FBbt_ids.tsv` | `FBbt_id` |
| `VNC_new_cells.owl` | `VNC_neurons/` | `VNCtable2.tsv`, `Feng.tsv` | `FBbt_ID` |

## Workflow

Process each FBbt ID in order. For each:

### Step 1: Validate

1. Convert the FBbt ID to underscore IRI format (e.g., `FBbt:20000000` → `FBbt_20000000`).
2. Search for the term in component OWL files:
   ```
   grep -l "FBbt_NNNNNNN" src/ontology/components/*.owl
   ```
3. Confirm the term is NOT already in fbbt-edit.obo:
   ```
   grep "^id: FBbt:NNNNNNN" src/ontology/fbbt-edit.obo
   ```
4. If the term is already in fbbt-edit.obo, skip it and report. If not found in any component, report an error.

### Step 2: Extract the term from the component OWL file

Use ROBOT to filter the single term and convert to OBO format:

```bash
cd src/ontology
robot filter \
  --input components/COMPONENT.owl \
  --term "http://purl.obolibrary.org/obo/FBbt_NNNNNNN" \
  --signature true \
  --trim false \
  convert --output /tmp/extracted_term.obo
```

**Important:** The `--term` flag requires the full IRI (with `http://purl.obolibrary.org/obo/FBbt_NNNNNNN`), not the CURIE format. The `--signature true --trim false` flags are essential to include all axioms (is_a, relationships) even when target terms are not in the extracted module.

Read the output file and extract just the `[Term]` stanza (everything from `[Term]` to the next blank line). Discard the OBO header lines.

### Step 3: Clean up the OBO stanza

The extracted stanza needs several adjustments to match the format in fbbt-edit.obo:

1. **Remove the `namespace:` line** — `namespace: fly_anatomy.ontology` is redundant because fbbt-edit.obo has `default-namespace: fly_anatomy.ontology` in its header. Delete this line entirely.

2. **Add `! name` comments to `is_a:` lines** — For each `is_a: FBbt:XXXXX` line, look up the term name in fbbt-edit.obo and append ` ! term_name`. Example: `is_a: FBbt:00047095` → `is_a: FBbt:00047095 ! adult neuron`. Search for the name with:
   ```
   grep -A1 "^id: FBbt:XXXXX" src/ontology/fbbt-edit.obo
   ```
   If the parent term is in a component file rather than fbbt-edit.obo, search the component files or use the label from the extracted OWL.

3. **Add `! name` comments to `relationship:` lines** — For each `relationship: RO:XXXXX FBbt:YYYYY` line, look up both the relationship name and target term name, and append ` ! relationship_name target_name`. Example: `relationship: RO:0013002 FBbt:00007401` → `relationship: RO:0013002 FBbt:00007401 ! receives synaptic input in region antennal lobe`. To find the relationship label, check existing relationship lines in fbbt-edit.obo with the same relation ID. For target terms in components, grep the component OWL for the `rdfs:label`.

4. **Normalize ORCID URLs** — If `property_value:` lines contain `http://orcid.org/`, change to `https://orcid.org/` to match existing terms in fbbt-edit.obo.

5. **Verify the stanza structure matches** existing FBbt:2000xxxx terms in fbbt-edit.obo. The standard field order is:
   ```
   id:
   name:
   def: "..." [xrefs]
   comment:
   subset: (if any)
   synonym: "..." TYPE [xrefs]
   xref: (if any)
   is_a:
   relationship:
   property_value:
   is_obsolete: (if applicable)
   replaced_by: (if applicable)
   ```

### Step 4: Insert the term into fbbt-edit.obo

Insert the cleaned `[Term]` stanza in **numerical ID order** among existing terms. FBbt:2000xxxx terms are located starting around line 174890 in fbbt-edit.obo.

1. Find the correct insertion point by locating the term with the highest ID that is still less than the new term's ID.
2. Find the blank line after that term's stanza.
3. Insert the new `[Term]` stanza followed by a blank line.

Use the Edit tool for insertion. The stanza must be preceded by a blank line (which is the separator between OBO stanzas).

### Step 5: Remove the term from the component OWL file

Use ROBOT to remove the term from the component:

```bash
cd src/ontology
robot remove \
  --input components/COMPONENT.owl \
  --term "http://purl.obolibrary.org/obo/FBbt_NNNNNNN" \
  --trim true \
  --output components/COMPONENT.owl
```

Verify removal:
```
grep "FBbt_NNNNNNN" components/COMPONENT.owl
```

### Step 6: Remove from source TSV file(s)

1. Identify the source directory from the mapping table above.
2. Search ALL TSV files in that directory for the FBbt ID (check both `:` and `_` formats):
   ```
   grep -rl "FBbt:NNNNNNN\|FBbt_NNNNNNN" src/patterns/robot_template_projects/DIRECTORY/
   ```
3. For each TSV file found, remove the entire row containing the FBbt ID using the Edit tool.

**IMPORTANT:** Do NOT remove entries from `src/patterns/robot_template_projects/EM_synonyms/` mapping files. These are ID-based synonym mappings (linking external dataset names to FBbt IDs) that should persist regardless of where the term is defined. The EM synonyms are generated as a separate component and the mappings remain valid.

### Step 7: Report

After processing all terms, provide a summary:
- Terms successfully moved (ID, name, source component)
- Terms skipped (already in fbbt-edit.obo)
- Terms not found (not in any component)
- TSV files modified
- Any issues encountered

## Troubleshooting

- **ROBOT filter produces empty output:** Ensure you're using the full IRI format `http://purl.obolibrary.org/obo/FBbt_NNNNNNN` (underscores, not colons) with the `--term` flag.
- **Missing relationships in OBO output:** Ensure `--signature true --trim false` flags are used with `robot filter`.
- **Cannot find parent term name:** Some parent terms may only exist in component files. Search across all components: `grep -r "rdfs:label" components/*.owl | grep "FBbt_XXXXX"`.
- **Large component files are slow:** The larger files (hemibrain_new_cells.owl at 22MB, flywire_neurons.owl at 19MB) may take a minute to process with ROBOT. This is normal.
- **Term appears in multiple components:** A term should only be in one component file. If found in multiple, investigate before proceeding — this may indicate a problem.
