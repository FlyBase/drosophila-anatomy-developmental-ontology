# EM Neuropil Synonyms

This project creates an OWL file of brain region synonyms found in EM connectomics datasets, analogous to the EM_synonyms project for neuron names.

## Region name files

### Neuprint datasets

Region names were fetched from neuprint (neuprint.janelia.org) on 2026-03-31 using neuprint-python. For each dataset, the ROI (Region of Interest) list was obtained via the Cypher query `MATCH (m :Meta) RETURN m.roiInfo` and the ROI hierarchy via `m.roiHierarchy`.

| Dataset | neuprint version | Regions | Notes |
|---------|-----------------|---------|-------|
| hemibrain | hemibrain:v1.2.1 | 230 | Brain regions including individual AL glomeruli and PB glomeruli |
| manc | manc:v1.2.3 | 59 | VNC neuropils and nerves |
| male-cns | male-cns:v0.9 | 200 | Brain + VNC neuropil-level regions |
| optic-lobe | optic-lobe:v1.1 | 106 | Brain neuropil-level regions |

Individual optic lobe columns (ME, LO, LOP columns — ~5,200 in male-cns and ~2,600 in optic-lobe) were removed as they cannot be mapped to FBbt terms.

### FlyWire FAFB

78 lateralised neuropil names extracted from the column headers of `neuropil_synapse_table.csv.gz` (materialization version 783) at `gs://flywire-data/codex/data/fafb/783/neuropil_synapse_table.csv.gz`. Columns follow the pattern `input synapses in {region}`. UNASGD (unassigned) was excluded.

### BANC

307 region outlines fetched from the BANC neuroglancer segment properties at `gs://lee-lab_brain-and-nerve-cord-fly-connectome/region_outlines/segment_properties/info` (file timestamp 2024-09-25 18:26:54). These are region meshes from multiple atlases warped into BANC space:

| Source | Count | Description |
|--------|-------|-------------|
| ITO | 75 | Ito et al. midbrain neuropils and optic lobe regions |
| COURT | 28 | Court et al. VNC neuropils and tracts |
| MANC | 83 | MANC VNC neuropils, nerves, and tracts |
| SCHLEGEL | 116 | Schlegel et al. antennal lobe glomeruli |
| BANC | 5 | Broad groupings (CX, MB, brain_neuropil, optic, vnc_neuropil) |

Four uninformative BANC-level labels were removed: `dataset`, `hemibrain`, `midbrain`, `neuropil`.

The `banc_regions.tsv` file includes columns for source atlas and region type (midbrain, optic, vnc, nerve, tract, glomerulus) as well as the neuroglancer segment ID.

### File descriptions

- `{dataset}_regions.tsv` - Tab-separated mapping files with columns: dataset region name, FBbt_id, FBbt_name, notes. The `banc_regions.tsv` file has additional columns for source, region_type, and segment_id.
- `{dataset}_roi_hierarchy.json` - ROI hierarchy from neuprint showing how regions nest (e.g. CNS > CentralBrain > AL(L), or CNS > Optic(R) > ME(R) > ME(R)-columns > individual columns). Only available for neuprint datasets.
- `map_regions_to_fbbt.py` - Script to populate FBbt_id and FBbt_name columns in the TSV files. Can be re-run after adding new regions or datasets.

## Mapping to FBbt

Region names were mapped to FBbt terms using `map_regions_to_fbbt.py`. The script strips left/right suffixes (`(L)`/`(R)`/`_L`/`_R`) before lookup so both sides receive the same FBbt ID.

Many region abbreviations are ambiguous in FBbt (e.g. `PB` matches both protocerebral bridge and pharyngeal tracheal branch; `CA` matches both mushroom body calyx and embryonic crepine; `FLA` matches both flange and first lateral abdominal nerve). The script uses an explicit dictionary of ~230 abbreviation-to-FBbt mappings to resolve these ambiguities, rather than relying on synonym lookup alone. Antennal lobe glomeruli (e.g. `DA1`, `AL-DA1`) are looked up dynamically from fbbt-edit.obo by matching `antennal lobe glomerulus {name}`.

### Unmapped regions

- **`*-unspecified`** regions (male-cns: `CV-unspecified`, `CentralBrain-unspecified`, `Optic-unspecified`, `VNC-unspecified`) are catch-all categories for unassigned synapses.
- **`hemibrain`** in the hemibrain dataset is a dataset-level label, not a region.
- **Lobula layer 7** (`LO_L_layer_7`, `LO_R_layer_7` in male-cns and optic-lobe) has no FBbt term (FBbt has lobula layers 1-6 only).
- **`GF`** (hemibrain) is the giant fiber neuron, not a region.
- **`CRN`** (male-cns) is the copulation reporting neuron, not a region.
