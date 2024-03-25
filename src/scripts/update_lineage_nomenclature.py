import pandas as pd

# replace nomenclature columns in other lineage patterns with those from the neuroblast patterns

dir = '../patterns/data/all-axioms/'
lineage_pattern_files = {'seg_nbs': dir + 'neuroblastBySegment.tsv',
                         'neurons': dir + 'neuronByBirthStageAndNotchStatusFromNeuroblastAtDevStage.tsv'}
nb_pattern_file = dir + 'neuroblastAnnotations.tsv'

nomenclature_cols = ['ito_lee', 'hartenstein', 'primary', 'secondary', 'reference']

nb_pattern = pd.read_csv(nb_pattern_file, sep='\t', dtype='str')
nb_to_merge = nb_pattern[['defined_class'] + nomenclature_cols].rename(columns={'defined_class':'neuroblast'})

def choose_label(row, col_order):
    row['nb_label'] = ''
    for col in col_order:
        if (row['nb_label'] == '') and pd.notnull(row[col]) :
            row['nb_label'] = row[col]
            break
    return row

col_order_non_sec = ['primary', 'hartenstein', 'secondary', 'ito_lee']
col_order_sec = ['secondary', 'ito_lee', 'primary', 'hartenstein']

# update nb_label col in neuroblast file
nb_pattern = nb_pattern.apply(choose_label, axis=1, col_order=col_order_non_sec)
nb_pattern.to_csv(nb_pattern_file, sep='\t', index=None)

# update nomenclature cols then choose an nb_label for each lineage pattern file
for pat in lineage_pattern_files:
    lineage_data = pd.read_csv(lineage_pattern_files[pat], sep='\t', dtype='str')
    lineage_data.drop(columns=nomenclature_cols, inplace=True)
    merged_data = lineage_data.merge(nb_to_merge, how='left', on='neuroblast')
    if pat == 'seg_nbs':
        non_sec_merged_data = merged_data
        sec_merged_data = pd.DataFrame({})
    if pat == 'neurons':
        sec_merged_data = merged_data[merged_data['birth_notch'].isin(['FBbt:00047096','FBbt:00049541','FBbt:00049542'])]
        non_sec_merged_data = merged_data[~merged_data['birth_notch'].isin(['FBbt:00047096','FBbt:00049541','FBbt:00049542'])]
    non_sec_merged_data = non_sec_merged_data.apply(choose_label, axis=1, col_order=col_order_non_sec)
    if not sec_merged_data.empty:
        sec_merged_data = sec_merged_data.apply(choose_label, axis=1, col_order=col_order_sec)
        merged_data = pd.concat([non_sec_merged_data, sec_merged_data])
    else:
        merged_data = non_sec_merged_data

    
    merged_data.sort_index().to_csv(lineage_pattern_files[pat], sep='\t', index=None)
