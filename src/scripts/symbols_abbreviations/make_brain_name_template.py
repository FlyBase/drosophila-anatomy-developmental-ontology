#!/usr/bin/env python3
"""Build a ROBOT template for BrainName official abbreviations.

Reads a simple curated TSV with columns 'FBbt_id' and 'abbreviation' and writes
a ROBOT template that adds each abbreviation as an exact synonym of the term,
typed BRAIN_NAME_ABV and referenced to the BrainName paper (Ito et al. 2014).

Usage:
    python3 make_brain_name_template.py <input.tsv> <output_template.tsv>
"""
import re
import sys
from collections import OrderedDict
import pandas as pd

REFERENCE = "FlyBase:FBrf0224194"
SYNONYM_TYPE = "http://purl.obolibrary.org/obo/fbbt#BRAIN_NAME_ABV"


def load_mapping_file(input_file):
    """Read a TSV as DataFrame of strings, with surrounding whitespace stripped from cells."""
    return pd.read_csv(input_file, sep="\t", dtype=str)\
        .fillna("")\
        .apply(lambda column: column.str.strip())


def main(mapping, output_file):

    template_seed = OrderedDict([
        ("ID", "ID"),
        ("abbreviation", "A oboInOwl:hasExactSynonym"),
        ("reference", ">A oboInOwl:hasDbXref"),
        ("synonym_type", ">AI oboInOwl:hasSynonymType"),
    ])
    template_header = pd.DataFrame.from_records([template_seed])
    
    template_body = mapping.rename(columns = {'FBbt_id':'ID'})
    template_body["reference"] = REFERENCE
    template_body["synonym_type"] = SYNONYM_TYPE
    
    template = pd.concat([template_header, template_body], ignore_index=True, sort=False)
    template.to_csv(output_file, sep="\t", header=True, index=False)


if __name__ == "__main__":
    main(load_mapping_file(sys.argv[1]), sys.argv[2])
