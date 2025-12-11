import pandas as pd
import shutil
import re

# update files from local copies (requires relevant mapping repos in same parent folder as fbbt repo)
source_filepaths = {'OL':'../../../../../neuprint_optic_lobe_curation/OL_FBbt_mapping.tsv',
                    'manc':'../../../../../manc_curation/resources/manc_cell_type_fbbt_mapping.tsv',
                    'flywire':'../../../../../FlyWire_curation/src/resources/flywire_fbbt_mapping.tsv',
                    'hemibrain':'../../../../../hemibrain_metadata/hemibrain_1-2_type_mapping.tsv',
                    'mc':'../../../../../male-cns_curation/resources/all_male-cns_FBbt.tsv',
                    'banc':'../../../../../banc-curation/src/resources/all_banc_FBbt.tsv'}
local_filepaths = {s:f.split('/')[-1] for s,f in source_filepaths.items()}

synonym_types = ['name_in_neuprint_optic_lobe', 'name_in_manc', 'name_in_flywire_fafb', 'name_in_hemibrain', 'name_in_male-cns', 'name_in_banc']
data_sources = source_filepaths.keys()

update_files = True
if update_files:
    for s in data_sources:
        f = source_filepaths[s]
        shutil.copy2(f, f.split('/')[-1])


class Mapping:
    def __init__(self, source):
        self.source = source
        self.filename = local_filepaths[source]
        
        if self.source == 'OL':
            self.synonym_type = 'name_in_neuprint_optic_lobe'
            self.reference = 'FlyBase:FBrf0262545' #Nern2025
            self.synonym_column = 'OL_type'

        elif self.source == 'manc':
            self.synonym_type = 'name_in_manc'
            self.reference = 'doi:10.7554/eLife.97766.1' #Marin2024
            self.synonym_column = 'type'

        elif self.source == 'flywire':
            self.synonym_type = 'name_in_flywire_fafb'
            self.reference = 'FlyBase:FBrf0260535' #Schlegel2024
            self.synonym_column = 'primary_type'

        elif self.source == 'hemibrain':
            self.synonym_type = 'name_in_hemibrain'
            self.reference = 'FlyBase:FBrf0246888' #Scheffer2020
            self.synonym_column = 'np_type'

        elif self.source == 'mc':
            self.synonym_type = 'name_in_male-cns'
            self.reference = 'doi:10.1101/2025.10.09.680999' #Berg2025
            self.synonym_column = 'type'

        elif self.source == 'banc':
            self.synonym_type = 'name_in_banc'
            self.reference = 'doi:10.1101/2025.07.31.667571' #Bates2025
            self.synonym_column = 'type'
        else:
            raise ValueError(f'Invalid source dataset {self.source}')
        
        self.dataframe = pd.read_csv(self.filename, sep='\t', dtype='str')
        self.dataframe = self.dataframe[['FBbt_id', self.synonym_column, 'specificity']].drop_duplicates(ignore_index=True)
        
    def format_and_filter(self):
        """
        Drop anything that has no FBbt id or is not specific (including multiple FBbt ids).
        Make consistently-named 'synonym' column and return only this, ID, synonym type and ref.
        """
        modified_df = self.dataframe.rename({self.synonym_column: 'synonym'}, axis=1)
        modified_df = modified_df[modified_df['FBbt_id'].notna() & modified_df['specificity'].isna() & modified_df['synonym'].notna()]
        modified_df = modified_df[~modified_df['FBbt_id'].str.contains('|', regex=False)]
        modified_df = modified_df[['FBbt_id', 'synonym']]
        modified_df['synonym_type'] = f'http://purl.obolibrary.org/obo/fbbt#{self.synonym_type}'
        modified_df['ref'] = self.reference
        return modified_df


synonym_dataframes = []
for s in data_sources:
    synonym_mapping = Mapping(s)
    filtered_df = synonym_mapping.format_and_filter()
    synonym_dataframes.append(filtered_df)

all_synonyms = pd.concat(synonym_dataframes)

# make robot template
header = pd.DataFrame({'FBbt_id': ['ID'], 'label': ['LABEL'], 'TYPE': ['TYPE'], 
                       'synonym': ['A oboInOwl:hasExactSynonym'], 'ref': ['>A oboInOwl:hasDbXref'], 'synonym_type': ['>A oboInOwl:hasSynonymType'],
                       'superproperty': ['SP %']})

synonym_type_rows = pd.DataFrame({'FBbt_id': [f'http://purl.obolibrary.org/obo/fbbt#{s}' for s in synonym_types], 
                                  'label': synonym_types, 
                                  'TYPE': ['owl:AnnotationProperty'] * len(synonym_types), 
                                  'synonym': [''] * len(synonym_types), 
                                  'ref': [''] * len(synonym_types), 
                                  'synonym_type': [''] * len(synonym_types),
                                  'superproperty': ['http://www.geneontology.org/formats/oboInOwl#SynonymTypeProperty'] * len(synonym_types)})

all_synonyms['label'] = ''
all_synonyms['TYPE'] = 'owl:Class'
all_synonyms['superproperty'] = ''

template = pd.concat([header, synonym_type_rows, all_synonyms])
template.to_csv('template.tsv', sep='\t', index=None)
