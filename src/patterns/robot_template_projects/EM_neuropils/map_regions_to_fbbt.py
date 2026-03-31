#!/usr/bin/env python3
"""
Map EM dataset region names to FBbt terms.

Reads all *_regions.tsv files in this directory, looks up region names
in fbbt-edit.obo (by name and synonym), and writes the FBbt_id and
FBbt_name back into the TSV files. Left/right suffixes are stripped
for lookup so both sides get the same mapping.

Many region abbreviations are ambiguous in FBbt (e.g. 'PB' matches
both protocerebral bridge and pharyngeal tracheal branch), so an
explicit mapping dictionary is used for all known neuropil regions.
Antennal lobe glomeruli are looked up dynamically from the OBO file.

Usage:
    python3 map_regions_to_fbbt.py
"""

import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OBO_FILE = os.path.join(SCRIPT_DIR, '..', '..', '..', 'ontology', 'fbbt-edit.obo')

# --- Explicit mappings for known neuropil abbreviations ---
# These override synonym lookup to avoid ambiguity with non-neuropil terms.

EXPLICIT_MAP = {
    # Broad groupings
    'brain_neuropil': ('FBbt:00003624', 'adult brain'),
    'CentralBrain': ('FBbt:00047887', 'adult central brain'),
    'INP': ('FBbt:00040037', 'inferior neuropils'),
    'OL': ('FBbt:00003701', 'adult optic lobe'),
    'Optic': ('FBbt:00003701', 'adult optic lobe'),
    'optic': ('FBbt:00003701', 'adult optic lobe'),
    'PENP': ('FBbt:00045047', 'adult periesophageal neuropils'),
    'SNP': ('FBbt:00045030', 'superior neuropils'),
    'VLNP': ('FBbt:00045021', 'ventrolateral neuropils'),
    'vnc_neuropil': ('FBbt:00004052', 'adult ventral nerve cord'),

    # Brain neuropils
    'AB': ('FBbt:00110172', 'asymmetrical body'),
    'AL': ('FBbt:00007401', 'adult antennal lobe'),
    'AME': ('FBbt:00045003', 'accessory medulla'),
    'AMMC': ('FBbt:00003982', 'antennal mechanosensory and motor center'),
    'AOTU': ('FBbt:00007059', 'anterior optic tubercle'),
    'AOT': ('FBbt:00100337', 'adult anterior optic tract'),
    'ATL': ('FBbt:00045039', 'antler'),
    'AVLP': ('FBbt:00040043', 'anterior ventrolateral protocerebrum'),
    'BU': ('FBbt:00003682', 'bulb'),
    'CA': ('FBbt:00003685', 'mushroom body calyx'),
    'CAN': ('FBbt:00045051', 'cantle'),
    'CRE': ('FBbt:00045037', 'adult crepine'),
    'CV': ('FBbt:00004019', 'adult cervical connective'),
    'CX': ('FBbt:00003632', 'adult central complex'),
    'EB': ('FBbt:00003678', 'ellipsoid body'),
    'EPA': ('FBbt:00040040', 'epaulette'),
    'FB': ('FBbt:00003679', 'fan-shaped body'),
    'FLA': ('FBbt:00045050', 'flange'),
    'GA': ('FBbt:00040060', 'gall'),
    'GC': ('FBbt:00047941', 'great commissure'),
    'GNG': ('FBbt:00004013', 'gnathal ganglion'),
    'GOR': ('FBbt:00040039', 'gorget'),
    'IB': ('FBbt:00040050', 'inferior bridge'),
    'ICL': ('FBbt:00040049', 'inferior clamp'),
    'IPS': ('FBbt:00045046', 'inferior posterior slope'),
    'LA': ('FBbt:00003708', 'lamina'),
    'LAL': ('FBbt:00003681', 'adult lateral accessory lobe'),
    'LH': ('FBbt:00007053', 'adult lateral horn'),
    'LO': ('FBbt:00003852', 'lobula'),
    'LOP': ('FBbt:00003885', 'lobula plate'),
    'LX': ('FBbt:00040001', 'lateral complex'),
    'MB': ('FBbt:00005801', 'adult mushroom body'),
    'ME': ('FBbt:00003748', 'medulla'),
    'NO': ('FBbt:00003680', 'nodulus'),
    'OCG': ('FBbt:00049817', 'ocellar ganglion'),
    'PB': ('FBbt:00003668', 'protocerebral bridge'),
    'PED': ('FBbt:00003687', 'mushroom body pedunculus'),
    'PLP': ('FBbt:00040044', 'posterior lateral protocerebrum'),
    'POC': ('FBbt:00007427', 'posterior optic commissure'),
    'PRW': ('FBbt:00040051', 'prow'),
    'PVLP': ('FBbt:00040042', 'posterior ventrolateral protocerebrum'),
    'ROB': ('FBbt:00048509', 'adult round body'),
    'RUB': ('FBbt:00040038', 'rubus'),
    'SAD': ('FBbt:00045048', 'saddle'),
    'SCL': ('FBbt:00040048', 'superior clamp'),
    'SIP': ('FBbt:00045032', 'superior intermediate protocerebrum'),
    'SLP': ('FBbt:00007054', 'superior lateral protocerebrum'),
    'SMP': ('FBbt:00007055', 'superior medial protocerebrum'),
    'SPS': ('FBbt:00045040', 'superior posterior slope'),
    'VES': ('FBbt:00040041', 'vest'),
    'VMNP': ('FBbt:00040002', 'ventromedial neuropils'),
    'VNC': ('FBbt:00004052', 'adult ventral nerve cord'),
    'WED': ('FBbt:00045027', 'wedge'),
    'mALT': ('FBbt:00003985', 'adult medial antennal lobe tract'),

    # Mushroom body subdivisions
    'MB_CA': ('FBbt:00007385', 'calyx of adult mushroom body'),
    'MB_ML': ('FBbt:00007677', 'medial lobe of adult mushroom body'),
    'MB_PED': ('FBbt:00007453', 'pedunculus of adult mushroom body'),
    'MB_VL': ('FBbt:00015407', 'vertical lobe of adult mushroom body'),
    'dACA': ('FBbt:00045007', 'adult mushroom body dorsal accessory calyx'),
    'lACA': ('FBbt:00048332', 'adult mushroom body lateral accessory calyx'),
    'vACA': ('FBbt:00110991', 'adult mushroom body ventral accessory calyx'),
    'MB(+ACA)': ('FBbt:00005801', 'adult mushroom body'),

    # MB lobe compartments (hemibrain naming)
    'a1': ('FBbt:00100285', 'mushroom body alpha lobe slice 1'),
    'a2': ('FBbt:00100286', 'mushroom body alpha lobe slice 2'),
    'a3': ('FBbt:00100287', 'mushroom body alpha lobe slice 3'),
    "a'1": ('FBbt:00100282', "mushroom body alpha' lobe slice 1"),
    "a'2": ('FBbt:00100283', "mushroom body alpha' lobe slice 2"),
    "a'3": ('FBbt:00100284', "mushroom body alpha' lobe slice 3"),
    'b1': ('FBbt:00100280', 'mushroom body beta lobe slice 1'),
    'b2': ('FBbt:00100281', 'mushroom body beta lobe slice 2'),
    "b'1": ('FBbt:00100278', "mushroom body beta' lobe slice 1"),
    "b'2": ('FBbt:00100279', "mushroom body beta' lobe slice 2"),
    'g1': ('FBbt:00100273', 'mushroom body gamma lobe slice 1'),
    'g2': ('FBbt:00100274', 'mushroom body gamma lobe slice 2'),
    'g3': ('FBbt:00100275', 'mushroom body gamma lobe slice 3'),
    'g4': ('FBbt:00100276', 'mushroom body gamma lobe slice 4'),
    'g5': ('FBbt:00100277', 'mushroom body gamma lobe slice 5'),
    'aL': ('FBbt:00110651', 'mushroom body alpha lobe'),
    "a'L": ('FBbt:00110652', "mushroom body alpha' lobe"),
    'bL': ('FBbt:00110653', 'mushroom body beta lobe'),
    "b'L": ('FBbt:00110654', "mushroom body beta' lobe"),
    'gL': ('FBbt:00007686', 'mushroom body gamma lobe'),

    # Fan-shaped body layers
    'FBl1': ('FBbt:00007487', 'fan-shaped body layer 1'),
    'FBl2': ('FBbt:00007488', 'fan-shaped body layer 2'),
    'FBl3': ('FBbt:00007490', 'fan-shaped body layer 3'),
    'FBl4': ('FBbt:00007491', 'fan-shaped body layer 4'),
    'FBl5': ('FBbt:00007492', 'fan-shaped body layer 5'),
    'FBl6': ('FBbt:00007493', 'fan-shaped body layer 6'),
    'FBl7': ('FBbt:00110655', 'fan-shaped body layer 7'),
    'FBl8': ('FBbt:00110656', 'fan-shaped body layer 8'),
    'FBl9': ('FBbt:00047032', 'fan-shaped body layer 9'),
    'FB-column3': ('FBbt:00003679', 'fan-shaped body'),

    # Ellipsoid body domains
    'EBr1': ('FBbt:00007555', 'ellipsoid body inner posterior domain'),
    'EBr2r4': ('FBbt:00007556', 'ellipsoid body outer central domain'),
    'EBr3am': ('FBbt:00007553', 'ellipsoid body inner central domain'),
    'EBr3d': ('FBbt:00007553', 'ellipsoid body inner central domain'),
    'EBr3pw': ('FBbt:00007553', 'ellipsoid body inner central domain'),
    'EBr5': ('FBbt:00047034', 'ellipsoid body anterior domain'),
    'EBr6': ('FBbt:00007554', 'ellipsoid body outer posterior domain'),

    # Nodulus subdivisions
    'NO1': ('FBbt:00111052', 'nodulus 1'),
    'NO2': ('FBbt:00111053', 'nodulus 2'),
    'NO3': ('FBbt:00111054', 'nodulus 3'),

    # Protocerebral bridge glomeruli (hemibrain L1-L9/R1-R9 -> FBbt 1-9)
    'PB(L1)': ('FBbt:00111511', 'protocerebral bridge glomerulus 1'),
    'PB(R1)': ('FBbt:00111511', 'protocerebral bridge glomerulus 1'),
    'PB(L2)': ('FBbt:00003669', 'protocerebral bridge glomerulus 2'),
    'PB(R2)': ('FBbt:00003669', 'protocerebral bridge glomerulus 2'),
    'PB(L3)': ('FBbt:00003670', 'protocerebral bridge glomerulus 3'),
    'PB(R3)': ('FBbt:00003670', 'protocerebral bridge glomerulus 3'),
    'PB(L4)': ('FBbt:00003671', 'protocerebral bridge glomerulus 4'),
    'PB(R4)': ('FBbt:00003671', 'protocerebral bridge glomerulus 4'),
    'PB(L5)': ('FBbt:00003672', 'protocerebral bridge glomerulus 5'),
    'PB(R5)': ('FBbt:00003672', 'protocerebral bridge glomerulus 5'),
    'PB(L6)': ('FBbt:00003673', 'protocerebral bridge glomerulus 6'),
    'PB(R6)': ('FBbt:00003673', 'protocerebral bridge glomerulus 6'),
    'PB(L7)': ('FBbt:00003674', 'protocerebral bridge glomerulus 7'),
    'PB(R7)': ('FBbt:00003674', 'protocerebral bridge glomerulus 7'),
    'PB(L8)': ('FBbt:00003675', 'protocerebral bridge glomerulus 8'),
    'PB(R8)': ('FBbt:00003675', 'protocerebral bridge glomerulus 8'),
    'PB(L9)': ('FBbt:00003676', 'protocerebral bridge glomerulus 9'),
    'PB(R9)': ('FBbt:00003676', 'protocerebral bridge glomerulus 9'),

    # VNC neuropils
    'Ov': ('FBbt:00004091', 'adult accessory mesothoracic neuropil'),
    'ABDNM': ('FBbt:00110173', 'adult abdominal neuromere'),
    'ANm': ('FBbt:00110173', 'adult abdominal neuromere'),
    'AMNP': ('FBbt:00004091', 'adult accessory mesothoracic neuropil'),
    'AMNp': ('FBbt:00004091', 'adult accessory mesothoracic neuropil'),
    'HTct': ('FBbt:00047138', 'haltere neuropil'),
    'IntTct': ('FBbt:00047519', 'intermediate tectulum'),
    'LTct': ('FBbt:00047174', 'lower tectulum'),
    'NTct': ('FBbt:00047173', 'neck neuropil'),
    'WTct': ('FBbt:00047137', 'wing neuropil'),
    'mVAC': ('FBbt:00047176', 'medial ventral association center'),
    'ProNM-T1': ('FBbt:00110174', 'adult prothoracic neuromere'),
    'MesoNM-T2': ('FBbt:00110175', 'adult mesothoracic neuromere'),
    'MetaNM-T3': ('FBbt:00110176', 'adult metathoracic neuromere'),

    # Tectulum/UTct variants
    'HTct(UTct-T3)': ('FBbt:00047138', 'haltere neuropil'),
    'HTct_UTct_T3': ('FBbt:00047138', 'haltere neuropil'),
    'NTct(UTct-T1)': ('FBbt:00047173', 'neck neuropil'),
    'NTct_UTct_T1': ('FBbt:00047173', 'neck neuropil'),
    'WTct(UTct-T2)': ('FBbt:00047137', 'wing neuropil'),
    'WTct_UTct_T2': ('FBbt:00047137', 'wing neuropil'),

    # Leg neuropils
    'LegNp(T1)': ('FBbt:00047140', 'adult T1 leg neuropil'),
    'LegNp(T2)': ('FBbt:00047141', 'adult T2 leg neuropil'),
    'LegNp(T3)': ('FBbt:00047142', 'adult T3 leg neuropil'),
    'LNp_T1': ('FBbt:00047140', 'adult T1 leg neuropil'),
    'LNp_T2': ('FBbt:00047141', 'adult T2 leg neuropil'),
    'LNp_T3': ('FBbt:00047142', 'adult T3 leg neuropil'),

    # mVAC variants
    'mVAC(T1)': ('FBbt:00047176', 'medial ventral association center'),
    'mVAC(T2)': ('FBbt:00047176', 'medial ventral association center'),
    'mVAC(T3)': ('FBbt:00047176', 'medial ventral association center'),
    'mVAC_T1': ('FBbt:00047176', 'medial ventral association center'),
    'mVAC_T2': ('FBbt:00047176', 'medial ventral association center'),
    'mVAC_T3': ('FBbt:00047176', 'medial ventral association center'),

    # Other VNC
    'cervical_connective': ('FBbt:00004019', 'adult cervical connective'),
    'vnc-shell': ('FBbt:00004052', 'adult ventral nerve cord'),

    # Compound/partial region names
    'CRE(-ROB,-RUB)': ('FBbt:00045037', 'adult crepine'),
    'CRE(-RUB)': ('FBbt:00045037', 'adult crepine'),
    'LAL(-GA)': ('FBbt:00003681', 'adult lateral accessory lobe'),
    'SAD(-AMMC)': ('FBbt:00045048', 'saddle'),

    # Tracts
    'DLT': ('FBbt:00047540', 'dorsal lateral tract'),
    'DLV': ('FBbt:00047541', 'dorsal lateral tract of ventral cervical fasciculus'),
    'DMT': ('FBbt:00047539', 'dorsal median tract'),
    'VLT': ('FBbt:00047543', 'ventral lateral tract of ventral cervical fasciculus'),
    'VTV': ('FBbt:00047542', 'ventral median tract of ventral cervical fasciculus'),
    'MDT': ('FBbt:00047544', 'median dorsal abdominal tract'),
    'MDA': ('FBbt:00047544', 'median dorsal abdominal tract'),
    'ITD': ('FBbt:00047534', 'intermediate tract of dorsal cervical fasciculus'),
    'ITD-CFF': ('FBbt:00047536', 'commissure of fine fibers of the ITD'),
    'ITD-HC': ('FBbt:00047838', 'intermediate tract of dorsal cervical fasciculus - haltere commissure'),
    'ITD-HT': ('FBbt:00049638', 'haltere tract'),
    'CVL': ('FBbt:00053285', 'adult curved ventrolateral tract'),
    'type-I_MTD': ('FBbt:00047546', 'type I median tract of dorsal cervical fasciculus'),
    'type-II_MTD': ('FBbt:00047547', 'type II median tract of dorsal cervical fasciculus'),
    'type-III_MTD': ('FBbt:00047548', 'type III median tract of dorsal cervical fasciculus'),

    # Nerves
    'AbN1': ('FBbt:00004105', 'adult first abdominal nerve'),
    'AbN2': ('FBbt:00004106', 'adult second abdominal nerve'),
    'AbN3': ('FBbt:00004107', 'adult third abdominal nerve'),
    'AbN4': ('FBbt:00004108', 'adult fourth abdominal nerve'),
    'AbNT': ('FBbt:00004099', 'adult abdominal nerve trunk'),
    'ADMN': ('FBbt:00004060', 'adult anterior dorsal mesothoracic nerve'),
    'CvN': ('FBbt:00004053', 'adult cervical nerve'),
    'DMetaN': ('FBbt:00004094', 'adult dorsal metathoracic nerve'),
    'DProN': ('FBbt:00004055', 'adult dorsal prothoracic nerve'),
    'MesoAN': ('FBbt:00004062', 'adult mesothoracic accessory nerve'),
    'MesoLN': ('FBbt:00004063', 'adult mesothoracic leg nerve'),
    'MetaLN': ('FBbt:00004096', 'adult metathoracic leg nerve'),
    'PDMN': ('FBbt:00004061', 'adult posterior dorsal mesothoracic nerve'),
    'PrN': ('FBbt:00007654', 'adult prosternal nerve'),
    'ProAN': ('FBbt:00004056', 'adult prothoracic accessory nerve'),
    'ProCN': ('FBbt:00049893', 'adult prothoracic chordotonal nerve'),
    'ProLN': ('FBbt:00007657', 'adult prothoracic leg nerve'),
    'VProN': ('FBbt:00004057', 'adult ventral prothoracic nerve'),
    'Xnerve': ('FBbt:00004098', 'adult X nerve'),

    # Medulla layers (neuprint uses 01-10, FBbt uses M1-M10)
    'ME_L_layer_01': ('FBbt:00003750', 'medulla layer M1'),
    'ME_R_layer_01': ('FBbt:00003750', 'medulla layer M1'),
    'ME_L_layer_02': ('FBbt:00003751', 'medulla layer M2'),
    'ME_R_layer_02': ('FBbt:00003751', 'medulla layer M2'),
    'ME_L_layer_03': ('FBbt:00003752', 'medulla layer M3'),
    'ME_R_layer_03': ('FBbt:00003752', 'medulla layer M3'),
    'ME_L_layer_04': ('FBbt:00003753', 'medulla layer M4'),
    'ME_R_layer_04': ('FBbt:00003753', 'medulla layer M4'),
    'ME_L_layer_05': ('FBbt:00003754', 'medulla layer M5'),
    'ME_R_layer_05': ('FBbt:00003754', 'medulla layer M5'),
    'ME_L_layer_06': ('FBbt:00003755', 'medulla layer M6'),
    'ME_R_layer_06': ('FBbt:00003755', 'medulla layer M6'),
    'ME_L_layer_07': ('FBbt:00003756', 'medulla serpentine layer'),
    'ME_R_layer_07': ('FBbt:00003756', 'medulla serpentine layer'),
    'ME_L_layer_08': ('FBbt:00003758', 'medulla layer M8'),
    'ME_R_layer_08': ('FBbt:00003758', 'medulla layer M8'),
    'ME_L_layer_09': ('FBbt:00003759', 'medulla layer M9'),
    'ME_R_layer_09': ('FBbt:00003759', 'medulla layer M9'),
    'ME_L_layer_10': ('FBbt:00003760', 'medulla layer M10'),
    'ME_R_layer_10': ('FBbt:00003760', 'medulla layer M10'),

    # Lobula layers
    'LO_L_layer_1': ('FBbt:00003853', 'lobula layer 1'),
    'LO_R_layer_1': ('FBbt:00003853', 'lobula layer 1'),
    'LO_L_layer_2': ('FBbt:00003854', 'lobula layer 2'),
    'LO_R_layer_2': ('FBbt:00003854', 'lobula layer 2'),
    'LO_L_layer_3': ('FBbt:00003855', 'lobula layer 3'),
    'LO_R_layer_3': ('FBbt:00003855', 'lobula layer 3'),
    'LO_L_layer_4': ('FBbt:00003856', 'lobula layer 4'),
    'LO_R_layer_4': ('FBbt:00003856', 'lobula layer 4'),
    'LO_L_layer_5': ('FBbt:00040016', 'lobula layer 5'),
    'LO_R_layer_5': ('FBbt:00040016', 'lobula layer 5'),
    'LO_L_layer_6': ('FBbt:00040017', 'lobula layer 6'),
    'LO_R_layer_6': ('FBbt:00040017', 'lobula layer 6'),

    # Lobula plate layers
    'LOP_L_layer_1': ('FBbt:00003886', 'lobula plate layer 1'),
    'LOP_R_layer_1': ('FBbt:00003886', 'lobula plate layer 1'),
    'LOP_L_layer_2': ('FBbt:00003887', 'lobula plate layer 2'),
    'LOP_R_layer_2': ('FBbt:00003887', 'lobula plate layer 2'),
    'LOP_L_layer_3': ('FBbt:00003888', 'lobula plate layer 3'),
    'LOP_R_layer_3': ('FBbt:00003888', 'lobula plate layer 3'),
    'LOP_L_layer_4': ('FBbt:00003889', 'lobula plate layer 4'),
    'LOP_R_layer_4': ('FBbt:00003889', 'lobula plate layer 4'),
}


def parse_obo_glomeruli(obo_path):
    """Look up antennal lobe glomerulus terms dynamically from OBO file."""
    glom_map = {}
    current_id = None
    current_name = None
    in_term = False
    obs = False

    with open(obo_path) as f:
        for line in f:
            line = line.rstrip()
            if line == '[Term]':
                if current_id and current_name and not obs:
                    m = re.match(r'^antennal lobe glomerulus (.+)$', current_name)
                    if m:
                        glom = m.group(1)
                        glom_map[glom] = (current_id, current_name)
                        glom_map[f'AL-{glom}'] = (current_id, current_name)
                current_id = None
                current_name = None
                in_term = True
                obs = False
            elif line.startswith('['):
                if current_id and current_name and not obs:
                    m = re.match(r'^antennal lobe glomerulus (.+)$', current_name)
                    if m:
                        glom = m.group(1)
                        glom_map[glom] = (current_id, current_name)
                        glom_map[f'AL-{glom}'] = (current_id, current_name)
                in_term = False
                current_id = None
            elif in_term:
                if line.startswith('id: '):
                    current_id = line[4:]
                elif line.startswith('name: '):
                    current_name = line[6:]
                elif line == 'is_obsolete: true':
                    obs = True

    if current_id and current_name and not obs:
        m = re.match(r'^antennal lobe glomerulus (.+)$', current_name)
        if m:
            glom = m.group(1)
            glom_map[glom] = (current_id, current_name)
            glom_map[f'AL-{glom}'] = (current_id, current_name)

    return glom_map


def strip_laterality(region):
    """Remove (L)/(R) or _L/_R suffixes."""
    region = re.sub(r'\(L\)$|\(R\)$', '', region)
    region = re.sub(r'_L$|_R$', '', region)
    return region.strip()


def update_tsv(filepath, mapping):
    """Read a regions TSV, fill in FBbt_id and FBbt_name columns, write back."""
    is_banc = 'banc' in os.path.basename(filepath)

    with open(filepath) as f:
        lines = f.readlines()

    header = lines[0].rstrip('\n')
    ncols = len(header.split('\t'))
    new_lines = [header + '\n']

    mapped = 0
    unmapped = 0

    for line in lines[1:]:
        parts = line.rstrip('\n').split('\t')
        while len(parts) < ncols:
            parts.append('')

        region = parts[0]
        region_stripped = strip_laterality(region)

        if region_stripped in mapping:
            tid, tname = mapping[region_stripped]
            if is_banc:
                parts[4] = tid
                parts[5] = tname
            else:
                parts[1] = tid
                parts[2] = tname
            mapped += 1
        else:
            unmapped += 1

        new_lines.append('\t'.join(parts) + '\n')

    with open(filepath, 'w') as f:
        f.writelines(new_lines)

    return mapped, unmapped


def main():
    obo_path = os.path.normpath(OBO_FILE)
    if not os.path.exists(obo_path):
        print(f"Error: OBO file not found at {obo_path}")
        return

    # Build complete mapping
    mapping = dict(EXPLICIT_MAP)

    # Add glomeruli from OBO
    glom_map = parse_obo_glomeruli(obo_path)
    mapping.update(glom_map)
    print(f"Loaded {len(glom_map) // 2} antennal lobe glomeruli from OBO file")

    # Process all TSV files
    tsv_files = sorted(f for f in os.listdir(SCRIPT_DIR) if f.endswith('_regions.tsv'))
    for fname in tsv_files:
        filepath = os.path.join(SCRIPT_DIR, fname)
        mapped, unmapped = update_tsv(filepath, mapping)
        print(f"{fname}: {mapped} mapped, {unmapped} unmapped")


if __name__ == '__main__':
    main()
