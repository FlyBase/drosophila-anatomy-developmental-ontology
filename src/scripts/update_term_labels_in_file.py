import pandas as pd
import argparse
from vfb_connect.neo.neo4j_tools import Neo4jConnect, dict_cursor

# connect to VFB KB
nc = Neo4jConnect('http://kb.virtualflybrain.org', 'neo4j', 'vfb')

# setup arguments that can be provided on command line
parser = argparse.ArgumentParser()

parser.add_argument("--filename", "-f", help="Filename")
parser.add_argument("--id_col", "-i", help="Name of column containing IDs")
parser.add_argument("--label_col", "-l", help="Name of column for labels")
parser.add_argument("--sep", "-s", help="Separator for lists")
args = parser.parse_args()

# if not running on command line, can edit defaults here:
if args.filename:
    file = args.filename
else:
    file = './file.tsv'
if args.id_col:
    id_column_name = args.id_col
else:
    id_column_name = 'FBbt_id'
if args.label_col:
    label_column_name = args.label_col
else:
    label_column_name = 'FBbt_name'
if args.sep:
    separator = args.sep
else:
    separator = '|'


def get_id_cols(filename=file):
    """Returns column names from the given file if 'FBbt:' is in the column."""
    mapping = pd.read_csv(filename, sep='\t', dtype=str)

    id_cols = []
    for col in mapping.columns:
        if len(mapping.loc[mapping[col].str.contains("FBbt", na=False)]) > 0:
            id_cols.append(col)

    return id_cols


def replace_labels(dataframe, id_col_name='FBbt_id', label_col_name='FBbt_name', sep='|'):
    """Updates labels from latest FBbt release (from VFB) based on IDs.

    Input is a dataframe - default for ID column to be 'FBbt_id' and label column as 'FBbt_name'.
    Label column not required in input."""
    col_order = dataframe.columns
    dataframe['converted_ids'] = dataframe.loc[:,id_col_name].apply(
        lambda x: (str(x).replace(':', '_')).split(sep))
    FBbt_list = list(dataframe.loc[:,'converted_ids'])
    flat_FBbt_list = list(set([item for sublist in FBbt_list for item in sublist]))

    # [str(x).replace(':', '_') for x in set(
    # dataframe[dataframe[id_col_name].notnull()][id_col_name])]

    query = ("MATCH (c:Class) WHERE c.short_form IN %s "
             "RETURN c.short_form AS ID, c.label AS label"
             % flat_FBbt_list)

    q = nc.commit_list([query])
    labels = dict_cursor(q)

    labels_df = pd.DataFrame(labels).set_index('ID')

# allow label column not to be present in original spreadsheet (and add to columns to return if not there)
    try:
        dataframe = dataframe.drop(label_col_name, axis=1)
    except KeyError:
        ID_col_loc = col_order.get_loc(id_col_name)
        col_order = col_order.insert(ID_col_loc + 1, label_col_name)

    def label_lookup(ID_list):
        """Looks up labels of items of a list of IDs in labels_df and returns list of labels."""
        label_list = []
        try:
            label_list = [labels_df.loc[i, 'label'] for i in ID_list]
        except KeyError:
            pass
        return label_list

# make column of lists of labels from column of lists of IDs
    dataframe['label_lists'] = dataframe.loc[:,'converted_ids'].apply(
        lambda x: label_lookup(x))
# convert lists to strings with separator
    dataframe[label_col_name] = dataframe.loc[:,'label_lists'].apply(
        lambda x: sep.join(x) if type(x) == list else x)

    dataframe = dataframe[col_order]
    return dataframe


def replace_labels_in_file(filename, id_col_name='FBbt_id', label_col_name='FBbt_name', sep='|'):
    """Updates labels from latest FBbt release (from VFB) based on IDs.

    Input is a file - default for ID column to be 'FBbt_id' and label column as 'FBbt_name'."""
    input_dataframe = pd.read_csv(filename, sep='\t', dtype=str)
    output_dataframe = replace_labels(input_dataframe, id_col_name, label_col_name, sep)

    output_dataframe.to_csv(filename, sep='\t', index=False)


if __name__ == "__main__":
    replace_labels_in_file(file, id_column_name, label_column_name, separator)
