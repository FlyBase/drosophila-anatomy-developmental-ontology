import pandas as pd

# replace nomenclature columns in other lineage patterns with those from the neuroblast patterns
dir = '../patterns/data/all-axioms/'
lineage_pattern_files = {'seg_nbs': dir + 'neuroblastBySegment.tsv',
                         'neurons': dir + 'neuronByBirthStageAndNotchStatusFromNeuroblastAtDevStage.tsv'}
nb_pattern_file = dir + 'neuroblastAnnotations.tsv'

nomenclature_cols = ['ito_lee', 'hartenstein', 'primary', 'secondary', 'reference', 'hartenstein_synonym_type', 'ito_lee_synonym_type', 'primary_synonym_type', 'secondary_synonym_type']

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

secondary_neuron = ['FBbt:00047096','FBbt:00049541','FBbt:00049542']
primary_neuron = ['FBbt:00047097', 'FBbt:00047105', 'FBbt:00047106']
notch_on_neuron = ['FBbt:00049539', 'FBbt:00049541', 'FBbt:00047106']
notch_off_neuron = ['FBbt:00049540', 'FBbt:00049542', 'FBbt:00047105']
adult = ['FBbt:00003004']


def neuron_name_printer(neuroblast, org_stage='', lineage_type='lineage', birth_stage=None, notch_status=None, vnc_secondary=False):
    if vnc_secondary:
        notch_dict = {'ON': 'A', 'OFF': 'B'}
        notch_letter = notch_dict.get(notch_status, '')
        neuron_name = f"{org_stage} {lineage_type} {neuroblast}{notch_letter}".strip()
        if birth_stage:
            neuron_name += f" {birth_stage}"
        neuron_name += " neuron"
    else:
        neuron_name = f"{org_stage} {neuroblast}".strip()
        if notch_status:
            neuron_name += f" Notch {notch_status}"
        neuron_name += f" {lineage_type}"
        if birth_stage:
            neuron_name += f" {birth_stage}"
        neuron_name += " neuron"

    return neuron_name


class lineageInfo:
    def __init__(self, table_row):
        self.table_row = table_row
        
        if table_row['birth_notch'] in secondary_neuron:
            self.prim_sec = 'secondary'
            self.emb_lv = ['larval-born','postembryonic']
        elif table_row['birth_notch'] in primary_neuron:
            self.prim_sec = 'primary'
            self.emb_lv = ['embryonic-born', 'embryonic']
        else:
            self.prim_sec = None
            self.emb_lv = None
        
        if table_row['birth_notch'] in notch_on_neuron:
            self.notch = 'ON'
            self.lin_type = 'hemilineage'
        elif table_row['birth_notch'] in notch_off_neuron:
            self.notch = 'OFF'
            self.lin_type = 'hemilineage'
        else:
            self.notch = None
            self.lin_type = 'lineage'

        if table_row.notnull()['other_types']:
            self.other = True
        else:
            self.other = False

        if table_row['other_types'] in secondary_neuron:
            self.other_prim_sec = 'secondary'
            self.other_emb_lv = ['larval-born','postembryonic']
        elif table_row['other_types'] in primary_neuron:
            self.other_prim_sec = 'primary'
            self.other_emb_lv = ['embryonic-born', 'embryonic']
        else:
            self.other_prim_sec = self.prim_sec
            self.other_emb_lv = self.emb_lv
        
        if table_row['other_types'] in notch_on_neuron:
            self.other_notch = 'ON'
            self.other_lin_type = 'hemilineage'
        elif table_row['other_types'] in notch_off_neuron:
            self.other_notch = 'OFF'
            self.other_lin_type = 'hemilineage'
        else:
            self.other_notch = self.notch
            self.other_lin_type = self.lin_type

        if table_row['stage'] in adult:
            self.stage = 'adult'
        else:
            self.stage = ''


    def write_names(self, colnames):
        other_synonyms = []
        for c in colnames:
            if self.table_row.notnull()[c]:
                neuron_name = neuron_name_printer(neuroblast = self.table_row[c], org_stage=self.stage, lineage_type=self.lin_type, birth_stage=self.prim_sec, notch_status=self.notch, vnc_secondary=(c=='secondary'))
                if self.emb_lv:
                    for e in self.emb_lv:
                        other_synonyms.append(neuron_name_printer(neuroblast = self.table_row[c], org_stage=self.stage, lineage_type=self.lin_type, birth_stage=e, notch_status=self.notch, vnc_secondary=(c=='secondary')))
                if self.other:
                    other_synonyms.append(neuron_name_printer(neuroblast = self.table_row[c], org_stage=self.stage, lineage_type=self.other_lin_type, birth_stage=self.other_prim_sec, notch_status=self.other_notch, vnc_secondary=(c=='secondary')))
                    if self.other_emb_lv:
                        for e in self.other_emb_lv:
                            other_synonyms.append(neuron_name_printer(neuroblast = self.table_row[c], org_stage=self.stage, lineage_type=self.other_lin_type, birth_stage=e, notch_status=self.other_notch, vnc_secondary=(c=='secondary')))
                self.table_row[c] = neuron_name
        self.table_row['other_synonyms'] = '|'.join(other_synonyms)
        return self.table_row


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
        # update nomenclature columns to names
        merged_data = merged_data.apply(lambda x: lineageInfo(x).write_names(col_order_non_sec), axis=1)
        # secondary or adult
        sec_merged_data = merged_data[merged_data['birth_notch'].isin(['FBbt:00047096','FBbt:00049541','FBbt:00049542']) | merged_data['stage'].isin(['FBbt:00003004'])]
        non_sec_merged_data = merged_data[~merged_data.index.isin(sec_merged_data.index)]
    non_sec_merged_data = non_sec_merged_data.apply(choose_label, axis=1, col_order=col_order_non_sec)
    if not sec_merged_data.empty:
        sec_merged_data = sec_merged_data.apply(choose_label, axis=1, col_order=col_order_sec)
        merged_data = pd.concat([non_sec_merged_data, sec_merged_data])
    else:
        merged_data = non_sec_merged_data

    
    merged_data.sort_index().to_csv(lineage_pattern_files[pat], sep='\t', index=None)
