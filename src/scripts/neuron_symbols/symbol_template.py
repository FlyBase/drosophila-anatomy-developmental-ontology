import pandas as pd
import os
import sys
from collections import OrderedDict
from alphabet_conversion import replace_spelled, replace_greek
from get_term_info import Term
from oaklib import get_adapter

def check_mapping_file(symbols_input_file):
    """Check for duplicate FBbt IDs and symbols in symbols_input_file.
    Also strips extra spaces in cells."""
    input = pd.read_csv(symbols_input_file, sep='\t')\
        .fillna("")\
        .applymap(str)\
        .applymap(lambda y: y.strip())

    dup_FBbt = list(input['FBbt_id'].value_counts()[
                                       input['FBbt_id'].value_counts() > 1].index)
    if len(dup_FBbt) > 0:
        raise ValueError('Duplicate FBbt IDs in mapping file! - ', dup_FBbt)

    dup_symbol = list(input['symbol'].value_counts()[
                                       input['symbol'].value_counts() > 1].index)
    if len(dup_symbol) > 0:
        raise ValueError('Duplicate symbols in mapping file! - ', dup_symbol)
    
    input.to_csv(symbols_input_file, sep="\t", header=True, index=False)


def symbol_template_maker(ontology_file, symbols_input_file, output_file):
    """Makes robot template from symbols_input_file.
    Input file should contain 'symbol', 'FBbt_id' and 'reference' columns."""
    
    # inputs
    ontology_adapter = get_adapter(ontology_file)
    symbol_table = pd.read_csv(symbols_input_file, sep='\t')\

    # prepare an empty template:
    template_seed = OrderedDict([('ID', 'ID'), ('CLASS_TYPE', 'CLASS_TYPE'),
                                 ('RDF_Type', 'TYPE'), ("Symbol", "A IAO:0000028"),
                                 ('ref1', ">A oboInOwl:hasDbXref"),
                                 ('Synonym_gr', "A oboInOwl:hasExactSynonym"),
                                 ('ref2', ">A oboInOwl:hasDbXref"),
                                 ('Synonym_en', "A oboInOwl:hasExactSynonym"),
                                 ('ref3', ">A oboInOwl:hasDbXref")])
    template = pd.DataFrame.from_records([template_seed])
    
    # Make a Term for each row of symbols_input_file and add details to template
    for i in symbol_table.index:
        
        FBbt_term = Term(ontology=ontology_adapter, 
                         id=symbol_table['FBbt_id'][i], 
                         symbol=replace_spelled(symbol_table.symbol[i]), 
                         reference = symbol_table['reference'][i])
        """try:
            FBbt_term.reference = symbol_table['reference'][i]
        except ValueError:
            pass"""
            
        FBbt_term.get_synonym_info()
        FBbt_term.check_existing_info()

        row_od = OrderedDict([])  # new template row as an empty ordered dictionary
        for c in template.columns:  # make columns and blank data for new template row
            row_od.update([(c, "")])

        # these are the same in each row
        row_od["CLASS_TYPE"] = "subclass"
        row_od["RDF_Type"] = "owl:Class"

        # ID, symbol
        row_od['ID'] = FBbt_term.id
        row_od["Symbol"] = FBbt_term.symbol
        if FBbt_term.reference:
            row_od["ref1"] = FBbt_term.reference

        # synonyms if not present
        if FBbt_term.add_as_synonym_gr:
            row_od["Synonym_gr"] = FBbt_term.symbol
            if FBbt_term.reference:
                row_od["ref2"] = FBbt_term.reference
        if FBbt_term.add_as_synonym_en:
            row_od["Synonym_en"] = replace_greek(FBbt_term.symbol)
            if FBbt_term.reference:
                row_od["ref3"] = FBbt_term.reference

        # make new row into a DataFrame and add it to template
        new_row = pd.DataFrame.from_records([row_od])
        template = pd.concat([template, new_row], ignore_index=True, sort=False)

    template.to_csv(output_file, sep="\t", header=True, index=False)

if __name__ == "__main__":
    check_mapping_file(symbols_input_file=sys.argv[2])
    symbol_template_maker(ontology_file=sys.argv[1], symbols_input_file=sys.argv[2], output_file=sys.argv[3])
