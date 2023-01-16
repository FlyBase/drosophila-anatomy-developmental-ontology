import update_term_labels_in_file
import argparse

parser = argparse.ArgumentParser()

parser.add_argument("--filename", "-f", help="Filename")
args = parser.parse_args()

id_cols = update_term_labels_in_file.get_id_cols(args.filename)

for id_col in id_cols:
    label_col = id_col + '_label'
    update_term_labels_in_file.replace_labels_in_file(args.filename, id_col_name=id_col, label_col_name=label_col, sep='|')
