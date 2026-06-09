#!/usr/bin/env python3
"""Build a ROBOT template for BrainName official abbreviations.

Reads a simple curated TSV with columns 'FBbt_id', 'symbol' and 'reference' and writes
a ROBOT template that adds symbol and typed synonym.
Symbols use greek characters where applicable, synonyms use spelled out 
and greek (if applicable) versions.

Usage:
    python3 symbol_template.py <input.tsv> <output_template.tsv>
"""

import pandas as pd
import sys
from collections import OrderedDict
from alphabet_conversion import replace_spelled, replace_greek

SYNONYM_TYPE = "http://purl.obolibrary.org/obo/fbbt#VFB_SYMBOL"

def load_mapping_file(symbols_input_file):
    """Read a TSV as DataFrame of strings, with surrounding whitespace stripped from cells."""
    return pd.read_csv(symbols_input_file, sep="\t", dtype=str)\
        .fillna("")\
        .apply(lambda column: column.str.strip())

def main(symbols_mapping, output_file):
    """Makes robot template from symbols_input_file.
    Input file should contain 'symbol', 'FBbt_id' and 'reference' columns."""

    # template header:
    template_seed = OrderedDict([('ID', 'ID'), ("Symbol", "A IAO:0000028"),
                                 ('ref1', ">A oboInOwl:hasDbXref SPLIT=|"),
                                 ('Synonym_gr', "A oboInOwl:hasExactSynonym"),
                                 ('ref2', ">A oboInOwl:hasDbXref SPLIT=|"),
                                 ('Synonym_type', ">AI oboInOwl:hasSynonymType"),
                                 ('Synonym_en', "A oboInOwl:hasExactSynonym"),
                                 ('ref3', ">A oboInOwl:hasDbXref SPLIT=|")])
    template_header = pd.DataFrame.from_records([template_seed])
    
    # convert input file to template body
    template_body = symbols_mapping.rename(columns = {'FBbt_id':'ID', 'symbol':'Symbol', 'reference':'ref1'})
    template_body["Symbol"] = template_body['Symbol'].apply(replace_spelled)
    template_body["Synonym_type"] = SYNONYM_TYPE
    template_body["ref2"] = template_body["ref1"]
    template_body["Synonym_gr"] = template_body['Symbol'].apply(replace_spelled)
    template_body["Synonym_en"] = template_body['Synonym_gr'].apply(lambda x: replace_greek(x) if x is not replace_greek(x) else "")
    template_body["ref3"] = template_body[template_body["Synonym_en"].notna()]['ref1']
    
    # concatenate
    template = pd.concat([template_header, template_body], ignore_index=True, sort=False)

    template.to_csv(output_file, sep="\t", header=True, index=False)

if __name__ == "__main__":
    main(load_mapping_file(sys.argv[1]), output_file=sys.argv[2])
