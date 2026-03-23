import pandas as pd

# This script propagates neuroblast nomenclature (from multiple naming systems)
# into the downstream DOSDP pattern TSV files for neurons, clones, and segment neuroblasts.
# It also generates human-readable neuron/clone names from the nomenclature columns.

# --- File paths for all DOSDP pattern TSV files that need nomenclature updates ---
pat_dir = '../patterns/data/all-axioms/'
lineage_pattern_files = {'seg_nbs': pat_dir + 'neuroblastBySegment.tsv',
                         'neurons': pat_dir + 'neuronByBirthStageAndNotchStatusFromNeuroblastAtDevStage.tsv',
                         'clones': pat_dir + 'cloneWithNeuroblastAndStage.tsv'}
# The neuroblast annotations file is the source of truth for nomenclature
nb_pattern_file = pat_dir + 'neuroblastAnnotations.tsv'

# Columns containing naming system data (Ito/Lee, Hartenstein, etc.) and their synonym types.
# These get replaced in downstream files with the latest values from neuroblastAnnotations.
nomenclature_cols = ['ito_lee', 'hartenstein', 'primary', 'secondary', 'technau', 'reference', 'technau_reference', 'hartenstein_synonym_type', 'ito_lee_synonym_type', 'primary_synonym_type', 'secondary_synonym_type', 'technau_synonym_type']

# Load the neuroblast annotations and extract just the neuroblast ID + nomenclature columns
# for merging into the other pattern files
nb_pattern = pd.read_csv(nb_pattern_file, sep='\t', dtype='str', na_filter=False)
nb_to_merge = nb_pattern[['defined_class'] + nomenclature_cols].rename(columns={'defined_class':'neuroblast'})

def choose_label(row, col_order):
    """Pick the first non-empty nomenclature value as the nb_label, using the given priority order."""
    row['nb_label'] = ''
    for col in col_order:
        if (row['nb_label'] == '') and row[col]:
            row['nb_label'] = row[col]
            break
    return row

# Priority order for choosing the preferred label.
# For secondary/adult neurons, the 'secondary' naming system takes priority;
# for everything else, 'primary' (i.e. Truman/Bate) takes priority.
col_order_non_sec = ['primary', 'hartenstein', 'secondary', 'ito_lee', 'technau']
col_order_sec = ['secondary', 'ito_lee', 'primary', 'hartenstein', 'technau']

# FBbt IDs for neuron birth-stage/Notch-status categories.
# These are used to determine whether a neuron is primary vs secondary
# and Notch ON vs Notch OFF, which affects how its name is constructed.
secondary_neuron = ['FBbt:00047096','FBbt:00049541','FBbt:00049542']  # secondary, secondary Notch ON, secondary Notch OFF
primary_neuron = ['FBbt:00047097', 'FBbt:00047105', 'FBbt:00047106']  # primary, primary Notch OFF, primary Notch ON
notch_on_neuron = ['FBbt:00049539', 'FBbt:00049541', 'FBbt:00047106']  # Notch ON, secondary Notch ON, primary Notch ON
notch_off_neuron = ['FBbt:00049540', 'FBbt:00049542', 'FBbt:00047105']  # Notch OFF, secondary Notch OFF, primary Notch OFF
adult = ['FBbt:00003004']  # adult stage


def neuron_name_printer(neuroblast, org_stage='', birth_stage=None, notch_status=None, vnc_secondary=False, notch_letter=False):
    """
    Build a human-readable neuron name string from its lineage components.

    Args:
        neuroblast: The neuroblast name from the relevant naming system.
        org_stage: Organism stage prefix (e.g. 'adult'), can be empty.
        birth_stage: 'primary', 'secondary', 'embryonic-born', etc.
        notch_status: 'Notch ON' or 'Notch OFF' (defines the hemilineage).
        vnc_secondary: If True, uses the VNC secondary naming convention where
            the neuroblast name comes after 'hemilineage'/'lineage'
            (e.g. "hemilineage 12A" vs "NB5-2 Notch ON hemilineage").
        notch_letter: If True, uses letter codes A/B instead of 'Notch ON'/'Notch OFF'.
    """
    notch_dict = {'Notch ON': 'A', 'Notch OFF': 'B'}
    notch_AB = notch_dict.get(notch_status, '')
    if vnc_secondary:
        # VNC secondary format: "hemilineage <NB><A/B> <birth_stage> neuron"
        if notch_status:
            neuron_name = f"{org_stage} hemilineage {neuroblast}{notch_AB}".strip()
        else:
            neuron_name = f"{org_stage} lineage {neuroblast}".strip()
        if birth_stage:
            neuron_name += f" {birth_stage}"
        neuron_name += " neuron"
    else:
        # Standard format: "<NB> <Notch status> hemilineage <birth_stage> neuron"
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
    """
    Parses a neuron pattern row to determine its birth stage (primary/secondary),
    Notch status (ON/OFF), and organism stage (adult or not). Also collects
    alternative birth-stage and Notch labels to generate synonym variants.
    """
    def __init__(self, table_row):
        self.table_row = table_row

        # Determine primary vs secondary from the birth_notch column
        if table_row['birth_notch'] in secondary_neuron:
            self.prim_sec = 'secondary'
            # Alternative labels that can substitute for 'secondary' in synonyms
            self.other_prim_sec = ['secondary', 'larval-born','postembryonic']
        elif table_row['birth_notch'] in primary_neuron:
            self.prim_sec = 'primary'
            self.other_prim_sec = ['primary', 'embryonic-born', 'embryonic']
        else:
            self.prim_sec = None
            self.other_prim_sec = [None]

        # Determine Notch signalling status from the birth_notch column
        if table_row['birth_notch'] in notch_on_neuron:
            self.notch = 'Notch ON'
        elif table_row['birth_notch'] in notch_off_neuron:
            self.notch = 'Notch OFF'
        else:
            self.notch = None

        # If an 'other_type' is specified (e.g. a less specific parent type),
        # expand the synonym alternatives to cover its birth-stage/Notch labels too
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
        """
        For each naming system column, generate the canonical neuron name and
        a set of alternative synonym forms (varying birth-stage labels, Notch
        status text vs letter codes). Writes names back into the table row and
        populates 'other_synonyms' with pipe-separated alternatives.
        """
        notch_dict = {'Notch ON': 'A', 'Notch OFF': 'B'}
        other_synonyms = []
        for c in colnames:
            if self.table_row[c]:
                # Generate the canonical name for this naming system
                neuron_name = neuron_name_printer(neuroblast = self.table_row[c], org_stage=self.stage, birth_stage=self.prim_sec, notch_status=self.notch, vnc_secondary=(c=='secondary'))
                # Generate all synonym variants by combining alternative
                # birth-stage labels with alternative Notch statuses
                for e in self.other_prim_sec:
                    for n in self.other_notch:
                        other_synonyms.append(neuron_name_printer(neuroblast = self.table_row[c], org_stage=self.stage, birth_stage=e, notch_status=n, vnc_secondary=(c=='secondary')))
                        # Also add letter-code variant (A/B) for non-VNC-secondary names
                        if n and not (c=='secondary'):
                            other_synonyms.append(neuron_name_printer(neuroblast = self.table_row[c], org_stage=self.stage, birth_stage=e, notch_status=n, notch_letter=True, vnc_secondary=(c=='secondary')))
                # Replace the raw nomenclature value with the full neuron name
                self.table_row[c] = neuron_name
                # Deduplicate and exclude the canonical name from synonyms
                other_synonyms = list(set([o for o in other_synonyms if o!=neuron_name]))
        self.table_row['other_synonyms'] = '|'.join(sorted(other_synonyms))
        return self.table_row

    def write_position_synonyms(self):
        """
        Generate position-based synonyms by combining IL_position with the ito_lee
        neuroblast name and H_position with the hartenstein neuroblast name,
        replacing the Notch status with the position term.
        E.g. 'CREa2 Notch OFF hemilineage neuron' + position 'ventral'
          -> 'CREa2 ventral hemilineage neuron'
        Writes the canonical synonym for each naming system to individual columns
        (il_position_synonym, h_position_synonym) for use as generated_synonyms
        in DOSDP. Any additional birth-stage variants are added to other_synonyms.
        """
        extra_synonyms = []
        # Pair each naming system with its position column and output column
        position_map = {
            'ito_lee': ('IL_position', 'il_position_synonym'),
            'hartenstein': ('H_position', 'h_position_synonym'),
        }
        for nom_col, (pos_col, out_col) in position_map.items():
            nb_name = self.table_row[nom_col]
            position = self.table_row.get(pos_col, '')
            if nb_name and position:
                # Extract the raw neuroblast name from the full neuron name
                # by taking text before ' Notch', ' hemilineage', or ' lineage'
                raw_nb = nb_name
                for marker in [' Notch ', ' hemilineage ', ' lineage ']:
                    if marker in raw_nb:
                        raw_nb = raw_nb[:raw_nb.index(marker)]
                        break
                # Strip any stage prefix (e.g. 'adult ') that was prepended by write_names
                if self.stage and raw_nb.startswith(self.stage + ' '):
                    raw_nb = raw_nb[len(self.stage) + 1:]
                # Canonical position synonym uses the primary birth-stage label
                canonical = neuron_name_printer(
                    neuroblast=raw_nb, org_stage=self.stage,
                    birth_stage=self.prim_sec, notch_status=position,
                    vnc_secondary=(nom_col == 'secondary'))
                self.table_row[out_col] = canonical
                # Additional birth-stage variants go into other_synonyms
                for e in self.other_prim_sec:
                    variant = neuron_name_printer(
                        neuroblast=raw_nb, org_stage=self.stage,
                        birth_stage=e, notch_status=position,
                        vnc_secondary=(nom_col == 'secondary'))
                    if variant != canonical:
                        extra_synonyms.append(variant)
            else:
                self.table_row[out_col] = ''
        # Append position variants to existing other_synonyms
        if extra_synonyms:
            existing = self.table_row.get('other_synonyms', '')
            all_synonyms = [s for s in existing.split('|') if s] + extra_synonyms
            self.table_row['other_synonyms'] = '|'.join(sorted(set(all_synonyms)))
        return self.table_row


def clone_name(df_row, nom_col):
    """Build a clone name like '<stage> <neuroblast name> lineage clone'."""
    if df_row[nom_col]:
        clone_name = ' '.join([df_row['stage_label'], df_row[nom_col], 'lineage clone']).strip()
        return clone_name
    else:
        return ''

# =====================================================================
# MAIN PROCESSING
# =====================================================================

# Step 1: Update the nb_label column in the neuroblast annotations file itself,
# picking the best available name using non-secondary priority order.
nb_pattern = nb_pattern.apply(choose_label, axis=1, col_order=col_order_non_sec)
nb_pattern.to_csv(nb_pattern_file, sep='\t', index=None)

# Step 2: For each downstream pattern file, refresh nomenclature from the
# neuroblast annotations, generate readable names, and pick the best label.
for pat in lineage_pattern_files:
    lineage_data = pd.read_csv(lineage_pattern_files[pat], sep='\t', dtype='str', na_filter=False)
    # Drop old nomenclature columns and re-merge fresh values from neuroblast annotations
    lineage_data.drop(columns=nomenclature_cols, inplace=True, errors='ignore')
    merged_data = lineage_data.merge(nb_to_merge, how='left', on='neuroblast')

    if pat == 'clones':
        # For clones, build clone names from each naming system
        for col in col_order_non_sec:
            merged_data[col] = merged_data.apply(lambda x: clone_name(x, col), axis=1)
        # Adult clones use the secondary label priority order
        sec_merged_data = merged_data[merged_data['stage'].isin(['FBbt:00003004'])]
        non_sec_merged_data = merged_data[~merged_data.index.isin(sec_merged_data.index)]

    elif pat == 'seg_nbs':
        # Segment neuroblasts don't have a secondary subset - just use standard priority
        non_sec_merged_data = merged_data
        sec_merged_data = pd.DataFrame({})

    elif pat == 'neurons':
        # For neurons, replace nomenclature values with full neuron name strings
        # and generate synonym variants, including position-based synonyms
        merged_data = merged_data.apply(lambda x: neuronLineageInfo(x).write_names(col_order_non_sec), axis=1)
        merged_data = merged_data.apply(lambda x: neuronLineageInfo(x).write_position_synonyms(), axis=1)
        merged_data.drop(columns=['position_synonyms'], inplace=True, errors='ignore')
        # Secondary neurons and adult neurons use the secondary label priority order
        sec_merged_data = merged_data[merged_data['birth_notch'].isin(['FBbt:00047096','FBbt:00049541','FBbt:00049542']) | merged_data['stage'].isin(['FBbt:00003004'])]
        non_sec_merged_data = merged_data[~merged_data.index.isin(sec_merged_data.index)]

    # Apply the appropriate label priority order to each subset
    if not non_sec_merged_data.empty:
        non_sec_merged_data = non_sec_merged_data.apply(choose_label, axis=1, col_order=col_order_non_sec)
    if not sec_merged_data.empty:
        sec_merged_data = sec_merged_data.apply(choose_label, axis=1, col_order=col_order_sec)
        merged_data = pd.concat([non_sec_merged_data, sec_merged_data])
    else:
        merged_data = non_sec_merged_data

    # Write the updated pattern file back, preserving original row order
    merged_data.sort_index().to_csv(lineage_pattern_files[pat], sep='\t', index=None)
