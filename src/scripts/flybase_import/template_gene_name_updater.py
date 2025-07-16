#!/usr/bin/env python3

import sys
import pandas as pd

pattern_files = ['../patterns/data/logical-only/ORNeuronByExpression.tsv']
template = pd.read_csv('tmp/FBgn_template.tsv', sep='\t', dtype='str')
gene_names = template[['ID', 'Label']].set_index('ID')

def detect_FBgn_cols(dataframe):
    "Identify columns that contain 'FBgn'."
    id_cols = []
    for col in dataframe.columns:
        if len(dataframe.loc[dataframe[col].str.contains("FBgn", na=False)]) > 0:
            id_cols.append(col)
    return id_cols

def label_list_lookup(ID_string, sep='|'):
    """Splits on sep and looks up labels of items of a list of IDs in gene_names and returns list of labels.
    Silent exit if input is not a string or IDs missing from gene_names."""
    label_list = []
    try:
        ID_list = ID_string.split(sep)
        label_list = [gene_names.loc[i, 'Label'] for i in ID_list]
    except:
        return None
    return sep.join(label_list)

for pat in pattern_files:
    pat_df = pd.read_csv(pat, sep='\t', dtype='str')
    col_order = pat_df.columns
    fbgn_cols = detect_FBgn_cols(pat_df)
    for col in fbgn_cols:
        label_col_name = col + '_label'
        try:
            pat_df.drop(label_col_name, axis=1)
        except KeyError:
            ID_col_loc = col_order.get_loc(col)
            col_order = col_order.insert(ID_col_loc + 1, label_col_name)

    # update labels
    pat_df[label_col_name] = pat_df.loc[:, col].apply(label_list_lookup)

    pat_df = pat_df[col_order]
    pat_df.to_csv(pat, index=False, sep='\t')
