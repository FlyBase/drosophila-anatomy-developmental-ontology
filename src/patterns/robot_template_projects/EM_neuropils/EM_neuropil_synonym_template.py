#!/usr/bin/env python3
"""
Generate a ROBOT template for EM neuropil region synonyms.

Reads each *_regions.tsv file and produces a template.tsv that ROBOT
can use to create an OWL file with related synonyms annotated by
dataset-specific synonym types and publication references.

Usage:
    python3 EM_neuropil_synonym_template.py
    robot template --input-iri http://purl.obolibrary.org/obo/fbbt.owl \
        --template template.tsv \
        annotate --ontology-iri "http://purl.obolibrary.org/obo/fbbt/EM_neuropil_synonyms.owl" \
        --output EM_neuropil_synonyms.owl
"""

import pandas as pd
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Dataset configurations: file, region column, synonym type, reference
DATASETS = {
    'hemibrain': {
        'file': 'hemibrain_regions.tsv',
        'region_col': 'hemibrain_region',
        'synonym_type': 'name_in_hemibrain',
        'reference': 'FlyBase:FBrf0246888',  # Scheffer2020
    },
    'manc': {
        'file': 'manc_regions.tsv',
        'region_col': 'manc_region',
        'synonym_type': 'name_in_manc',
        'reference': 'doi:10.7554/eLife.97766.1',  # Marin2024
    },
    'male-cns': {
        'file': 'male-cns_regions.tsv',
        'region_col': 'male-cns_region',
        'synonym_type': 'name_in_male-cns',
        'reference': 'doi:10.1101/2025.10.09.680999',  # Berg2025
    },
    'optic-lobe': {
        'file': 'optic-lobe_regions.tsv',
        'region_col': 'optic-lobe_region',
        'synonym_type': 'name_in_neuprint_optic_lobe',
        'reference': 'FlyBase:FBrf0262545',  # Nern2025
    },
    'flywire': {
        'file': 'flywire_regions.tsv',
        'region_col': 'flywire_region',
        'synonym_type': 'name_in_flywire_fafb',
        'reference': 'FlyBase:FBrf0260535',  # Schlegel2024
    },
    'banc': {
        'file': 'banc_regions.tsv',
        'region_col': 'banc_region',
        'synonym_type': 'name_in_banc',
        'reference': 'doi:10.1101/2025.07.31.667571',  # Bates2025
    },
}

synonym_types = sorted(set(d['synonym_type'] for d in DATASETS.values()))


def load_dataset(name, config):
    """Load a regions TSV and return synonym rows."""
    filepath = os.path.join(SCRIPT_DIR, config['file'])
    df = pd.read_csv(filepath, sep='\t', dtype='str')

    region_col = config['region_col']
    is_banc = name == 'banc'
    fbbt_col = 'FBbt_id'

    # Keep only rows with FBbt mappings
    df = df[df[fbbt_col].notna() & (df[fbbt_col] != '')]

    rows = []
    for _, row in df.iterrows():
        fbbt_id = row[fbbt_col]
        region = row[region_col]
        if not region or not fbbt_id:
            continue
        rows.append({
            'FBbt_id': fbbt_id,
            'synonym': region,
            'synonym_type': f'http://purl.obolibrary.org/obo/fbbt#{config["synonym_type"]}',
            'ref': config['reference'],
        })

    return pd.DataFrame(rows)


def main():
    # Collect all synonyms
    all_dfs = []
    for name, config in DATASETS.items():
        df = load_dataset(name, config)
        print(f"{name}: {len(df)} synonym rows")
        all_dfs.append(df)

    all_synonyms = pd.concat(all_dfs, ignore_index=True)

    # Deduplicate: same FBbt_id + synonym + synonym_type
    all_synonyms = all_synonyms.drop_duplicates(
        subset=['FBbt_id', 'synonym', 'synonym_type'], ignore_index=True
    )
    print(f"Total unique synonyms: {len(all_synonyms)}")

    # Build ROBOT template
    # Row 1: ROBOT header
    header = pd.DataFrame([{
        'FBbt_id': 'ID',
        'label': 'LABEL',
        'TYPE': 'TYPE',
        'synonym': 'A oboInOwl:hasRelatedSynonym',
        'ref': '>A oboInOwl:hasDbXref',
        'synonym_type': '>A oboInOwl:hasSynonymType',
        'superproperty': 'SP %',
    }])

    # Synonym type annotation property declarations
    syn_type_rows = pd.DataFrame([{
        'FBbt_id': f'http://purl.obolibrary.org/obo/fbbt#{st}',
        'label': st,
        'TYPE': 'owl:AnnotationProperty',
        'synonym': '',
        'ref': '',
        'synonym_type': '',
        'superproperty': 'http://www.geneontology.org/formats/oboInOwl#SynonymTypeProperty',
    } for st in synonym_types])

    # Synonym data rows
    all_synonyms['label'] = ''
    all_synonyms['TYPE'] = 'owl:Class'
    all_synonyms['superproperty'] = ''

    template = pd.concat([header, syn_type_rows, all_synonyms], ignore_index=True)

    outpath = os.path.join(SCRIPT_DIR, 'template.tsv')
    template.to_csv(outpath, sep='\t', index=False)
    print(f"Wrote {outpath} ({len(template)} rows including header)")


if __name__ == '__main__':
    main()
