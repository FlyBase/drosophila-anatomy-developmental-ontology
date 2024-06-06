import pandas as pd
import argparse

# setup arguments that can be provided on command line
parser = argparse.ArgumentParser()

parser.add_argument("--filename", "-f", help="Filename")
parser.add_argument("--id_col", "-i", help="Name of column containing IDs or 'auto' to autodetect column(s)")
parser.add_argument("--label_col", "-l", help="Name of column for labels (if -i is 'auto', '{id_col}_label' will be used)")
parser.add_argument("--sep", "-s", help="Separator for lists")
parser.add_argument("--source", "-c", help="Where to lookup labels ('VFB' or a filename)")
args = parser.parse_args()

# if not running on command line, can edit defaults here:
if args.filename:
    file = args.filename
else:
    file = './file.tsv'
if args.id_col:
    id_column_name = args.id_col
else:
    id_column_name = 'auto'
if args.label_col:
    label_column_name = args.label_col
else:
    label_column_name = 'term_label'
if args.sep:
    separator = args.sep
else:
    separator = '|'
if args.source:
    source = args.source
else:
    source = 'VFB'

# conditional imports
if source == 'VFB':
    from vfb_connect.neo.neo4j_tools import Neo4jConnect, dict_cursor
else:
    from oaklib import get_adapter


def get_id_cols(filename=file):
    """Returns column names from the given file if '^[A-z]+:[0-9]+$' is in the column."""
    mapping = pd.read_csv(filename, sep='\t', dtype=str)

    id_cols = []
    for col in mapping.columns:
        if len(mapping.loc[mapping[col].str.contains("^[A-z]+:[0-9]+$", na=False)]) > 0:
            id_cols.append(col)
    return id_cols


def replace_labels(dataframe, id_col_name=id_column_name, label_col_name=label_column_name, sep=separator, source=source):
    """Updates labels from latest FBbt release (from VFB) based on IDs.

    Input is a dataframe - default for ID column to be 'FBbt_id' and label column as 'FBbt_name'.
    Label column not required in input."""
    col_order = dataframe.columns
    # separate ids to lists and make one flat list of unique values
    dataframe['id_lists'] = dataframe[id_col_name].apply(lambda x: x.split(sep))
    flat_FBbt_list = list(set(dataframe['id_lists'].explode().tolist()))
    flat_FBbt_list = list(filter(None, flat_FBbt_list))  # remove Nones

    if source == 'VFB':  # get labels from VFB KB
        flat_FBbt_list_converted = [item.replace(':', '_') for item in flat_FBbt_list]

        nc = Neo4jConnect('http://kb.virtualflybrain.org', 'neo4j', 'vfb')
        query = ("MATCH (c:Class) WHERE c.short_form IN %s "
                 "RETURN c.short_form AS ID, c.label AS label"
                 % flat_FBbt_list_converted)

        q = nc.commit_list([query])
        labels = dict_cursor(q)
        labels_df = pd.DataFrame(labels)
        labels_df['ID'] = labels_df['ID'].apply(lambda x: x.replace('_', ':'))
        labels_df = labels_df.set_index('ID')

    else:  # get labels from local file
        ontology = get_adapter(source)
        labels_df = pd.DataFrame({})
        labels_df['ID'] = flat_FBbt_list
        labels_df['label'] = labels_df['ID'].apply(lambda x: ontology.label(x))
        labels_df = labels_df.set_index('ID')

    labels_df = labels_df[labels_df['label'].notnull()]

    def label_lookup(ID_list):
        """Looks up labels of items of a list of IDs in labels_df and returns list of labels."""
        label_list = []
        try:
            label_list = [labels_df.loc[i, 'label'] for i in ID_list]
        except KeyError:
            pass
        return label_list

    # allow label column not to be present in original spreadsheet (and add to columns to return if not there)
    try:
        dataframe = dataframe.drop(label_col_name, axis=1)
    except KeyError:
        ID_col_loc = col_order.get_loc(id_col_name)
        col_order = col_order.insert(ID_col_loc + 1, label_col_name)

    # make column of lists of labels from column of lists of IDs
    dataframe['label_lists'] = dataframe.loc[:, id_col_name].apply(
        lambda x: label_lookup(x.split(sep)))
    # convert lists to strings with separator
    dataframe[label_col_name] = dataframe.loc[:,'label_lists'].apply(
        lambda x: sep.join(x) if type(x) == list else x)

    dataframe = dataframe[col_order]
    return dataframe


def replace_labels_in_file(filename, id_col_name=id_column_name, label_col_name=label_column_name, sep=separator):
    """Updates labels from latest FBbt release (from VFB) based on IDs.

    Input is a file - default for ID column to be 'FBbt_id' and label column as 'FBbt_name'."""
    if id_col_name == 'auto':
        id_columns = get_id_cols(filename)
    else:
        id_columns = id_col_name

    dataframe = pd.read_csv(filename, sep='\t', dtype=str, na_filter=False)
    if not isinstance(id_columns, list):  # if only one column, make it a list
        id_columns = [id_columns]
    for i in id_columns:
        if id_col_name == 'auto':
            label_col_name = i + '_label'
        dataframe = replace_labels(dataframe, i, label_col_name, sep)

    dataframe.to_csv(filename, sep='\t', index=False)


if __name__ == "__main__":
    replace_labels_in_file(file, id_column_name, label_column_name, separator)
