# EM Neuropil Synonyms

This project creates an OWL file of brain region synonyms found in EM connectomics datasets, analogous to the EM_synonyms project for neuron names.

## Region name files

### Neuprint datasets

Region names were fetched from neuprint (neuprint.janelia.org) on 2026-03-31 using neuprint-python. For each dataset, the ROI (Region of Interest) list was obtained via the Cypher query `MATCH (m :Meta) RETURN m.roiInfo` and the ROI hierarchy via `m.roiHierarchy`.

| Dataset | neuprint version | Regions | Notes |
|---------|-----------------|---------|-------|
| hemibrain | hemibrain:v1.2.1 | 230 | Brain regions including individual AL glomeruli and PB glomeruli |
| manc | manc:v1.2.3 | 59 | VNC neuropils and nerves |
| male-cns | male-cns:v0.9 | 5,412 | Brain + VNC regions; includes ~5,250 individual optic lobe columns |
| optic-lobe | optic-lobe:v1.1 | 2,690 | Brain regions; includes ~2,600 individual optic lobe columns |

The large region counts for male-cns and optic-lobe are mostly individual columns in medulla (ME), lobula (LO), and lobula plate (LOP). The neuropil-level regions number ~80-150 per dataset.

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

- `{dataset}_regions.tsv` - Tab-separated mapping files with columns: dataset region name, FBbt_id, FBbt_name, notes. FBbt mappings are to be filled in.
- `{dataset}_roi_hierarchy.json` - ROI hierarchy from neuprint showing how regions nest (e.g. CNS > CentralBrain > AL(L), or CNS > Optic(R) > ME(R) > ME(R)-columns > individual columns). Only available for neuprint datasets.
