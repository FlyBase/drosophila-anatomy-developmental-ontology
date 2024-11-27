import pandas as pd

# replace nomenclature columns in other lineage patterns with those from the neuroblast patterns
pat_dir = '../patterns/data/all-axioms/'
lineage_pattern_files = {'seg_nbs': pat_dir + 'neuroblastBySegment.tsv',
                         'neurons': pat_dir + 'neuronByBirthStageAndNotchStatusFromNeuroblastAtDevStage.tsv',
                         'clones': pat_dir + 'cloneWithNeuroblastAndStage.tsv'}
nb_pattern_file = pat_dir + 'neuroblastAnnotations.tsv'

nomenclature_cols = ['ito_lee', 'hartenstein', 'primary', 'secondary', 'reference', 'hartenstein_synonym_type', 'ito_lee_synonym_type', 'primary_synonym_type', 'secondary_synonym_type']

nb_pattern = pd.read_csv(nb_pattern_file, sep='\t', dtype='str', na_filter=False)
nb_to_merge = nb_pattern[['defined_class'] + nomenclature_cols].rename(columns={'defined_class':'neuroblast'})

def choose_label(row, col_order):
    row['nb_label'] = ''
    for col in col_order:
        if (row['nb_label'] == '') and row[col]:
            row['nb_label'] = row[col]
            break
    return row

col_order_non_sec = ['primary', 'hartenstein', 'secondary', 'ito_lee']
col_order_sec = ['secondary', 'ito_lee', 'primary', 'hartenstein']

secondary_neuron = ['FBbt:00047096','FBbt:00049541','FBbt:00049542']
primary_neuron = ['FBbt:00047097', 'FBbt:00047105', 'FBbt:00047106']
notch_on_neuron = ['FBbt:00049539', 'FBbt:00049541', 'FBbt:00047106']
notch_off_neuron = ['FBbt:00049540', 'FBbt:00049542', 'FBbt:00047105']
adult = ['FBbt:00003004']


def neuron_name_printer(neuroblast, org_stage='', birth_stage=None, notch_status=None, vnc_secondary=False, notch_letter=False):
    notch_dict = {'Notch ON': 'A', 'Notch OFF': 'B'}
    notch_AB = notch_dict.get(notch_status, '')
    if vnc_secondary:
        if notch_status:
            neuron_name = f"{org_stage} hemilineage {neuroblast}{notch_AB}".strip()
        else:
            neuron_name = f"{org_stage} lineage {neuroblast}".strip()
        if birth_stage:
            neuron_name += f" {birth_stage}"
        neuron_name += " neuron"
    else:
        neuron_name = f"{org_stage} {neuroblast}".strip()
        if notch_letter:
            neuron_name += f" hemilineage {notch_AB}"
        elif notch_status:
            neuron_name += f" {notch_status} hemilineage"
        else:
            neuron_name += f" lineage"
        if birth_stage:
            neuron_name += f" {birth_stage}"
        neuron_name += " neuron"

    return neuron_name


class neuronLineageInfo:
    def __init__(self, table_row):
        self.table_row = table_row
        
        if table_row['birth_notch'] in secondary_neuron:
            self.prim_sec = 'secondary'
            self.other_prim_sec = ['secondary', 'larval-born','postembryonic']
        elif table_row['birth_notch'] in primary_neuron:
            self.prim_sec = 'primary'
            self.other_prim_sec = ['primary', 'embryonic-born', 'embryonic']
        else:
            self.prim_sec = None
            self.other_prim_sec = [None]
        
        if table_row['birth_notch'] in notch_on_neuron:
            self.notch = 'Notch ON'
        elif table_row['birth_notch'] in notch_off_neuron:
            self.notch = 'Notch OFF'
        else:
            self.notch = None
        
        if table_row['other_type']:
            other_type = table_row['other_type']

            if other_type in secondary_neuron:
                self.other_prim_sec.extend(['secondary', 'larval-born','postembryonic'])
            elif other_type in primary_neuron:
                self.other_prim_sec.extend(['primary', 'embryonic-born', 'embryonic'])
            
            if other_type in notch_on_neuron:
                self.other_notch = list(set([self.notch, 'Notch ON']))
            elif other_type in notch_off_neuron:
                self.other_notch = list(set([self.notch, 'Notch OFF']))
            else:
                self.other_notch = [self.notch]
        else:
            self.other_notch = [self.notch]

        if table_row['stage'] in adult:
            self.stage = 'adult'
        else:
            self.stage = ''


    def write_names(self, colnames):
        notch_dict = {'Notch ON': 'A', 'Notch OFF': 'B'}
        other_synonyms = []
        for c in colnames:
            if self.table_row[c]:
                neuron_name = neuron_name_printer(neuroblast = self.table_row[c], org_stage=self.stage, birth_stage=self.prim_sec, notch_status=self.notch, vnc_secondary=(c=='secondary'))
                for e in self.other_prim_sec:
                    for n in self.other_notch:
                        other_synonyms.append(neuron_name_printer(neuroblast = self.table_row[c], org_stage=self.stage, birth_stage=e, notch_status=n, vnc_secondary=(c=='secondary')))
                        if n and not (c=='secondary'):
                            other_synonyms.append(neuron_name_printer(neuroblast = self.table_row[c], org_stage=self.stage, birth_stage=e, notch_status=n, notch_letter=True, vnc_secondary=(c=='secondary')))
                self.table_row[c] = neuron_name
                other_synonyms = list(set([o for o in other_synonyms if o!=neuron_name]))
        self.table_row['other_synonyms'] = '|'.join(sorted(other_synonyms))
        return self.table_row


def clone_name(df_row, nom_col):
    if df_row[nom_col]:
        clone_name = ' '.join([df_row['stage_label'], df_row[nom_col], 'lineage clone']).strip()
        return clone_name
    else:
        return ''

# update nb_label col in neuroblast file
nb_pattern = nb_pattern.apply(choose_label, axis=1, col_order=col_order_non_sec)
nb_pattern.to_csv(nb_pattern_file, sep='\t', index=None)

# update nomenclature cols then choose an nb_label for each lineage pattern file
for pat in lineage_pattern_files:
    lineage_data = pd.read_csv(lineage_pattern_files[pat], sep='\t', dtype='str', na_filter=False)
    lineage_data.drop(columns=nomenclature_cols, inplace=True, errors='ignore')
    merged_data = lineage_data.merge(nb_to_merge, how='left', on='neuroblast')
    if pat == 'clones':
        for col in col_order_non_sec:
            merged_data[col] = merged_data.apply(lambda x: clone_name(x, col), axis=1)
        sec_merged_data = merged_data[merged_data['stage'].isin(['FBbt:00003004'])]
        non_sec_merged_data = merged_data[~merged_data.index.isin(sec_merged_data.index)]
    elif pat == 'seg_nbs':
        non_sec_merged_data = merged_data
        sec_merged_data = pd.DataFrame({})
    elif pat == 'neurons':
        # update nomenclature columns to names
        merged_data = merged_data.apply(lambda x: neuronLineageInfo(x).write_names(col_order_non_sec), axis=1)
        # secondary or adult
        sec_merged_data = merged_data[merged_data['birth_notch'].isin(['FBbt:00047096','FBbt:00049541','FBbt:00049542']) | merged_data['stage'].isin(['FBbt:00003004'])]
        non_sec_merged_data = merged_data[~merged_data.index.isin(sec_merged_data.index)]
    if not non_sec_merged_data.empty:
        non_sec_merged_data = non_sec_merged_data.apply(choose_label, axis=1, col_order=col_order_non_sec)
    if not sec_merged_data.empty:
        sec_merged_data = sec_merged_data.apply(choose_label, axis=1, col_order=col_order_sec)
        merged_data = pd.concat([non_sec_merged_data, sec_merged_data])
    else:
        merged_data = non_sec_merged_data

    
    merged_data.sort_index().to_csv(lineage_pattern_files[pat], sep='\t', index=None)
