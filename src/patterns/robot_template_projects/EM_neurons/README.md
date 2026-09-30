# EM connectome neuron terms

Script-driven generation of FBbt neuron terms from EM connectome datasets
(FlyWire/FAFB, hemibrain, MANC, male-CNS, optic lobe). Offline build scripts
produce a single component, `components/EM_neurons.owl`, from a **single ROBOT
template**.

> **Scope:** EM-connectome neuron terms only. `VNC_neurons/` (Feng/Ehrhardt) is
> **not** EM-derived and has its own component (`components/VNC_new_cells.owl`).
> BANC cross-dataset identity axioms are in `components/banc_identical_to.owl`.

## Layout

```
EM_neurons/
├── lib/
│   ├── EM_common.py        # shared helpers (name_lister, #1105 TYPE rows, NT->GO,
│   │                       #   laterality/connectivity filter, curation_path, ...)
│   └── EM_unified.py       # the unified ROBOT-template schema + per-connectome
│                           #   native->unified column maps + the row collector
├── build_EM_neurons.py     # the generator: runs the six row builders, unifies +
│                           #   registry-filters them, writes one template.tsv
├── registry/
│   ├── build_registry.py   # (re)build the registry from the build output + curation bridges
│   └── EM_neuron_registry.tsv   # committed: one row per FBbt id (single ID source;
│                                 #   move-to-edit removal target)
├── sources/                # committed curated inputs, per connectome
│   ├── manc/               # new_cell_FBbt_ids, typing_info, *_FBbt_map, ...
│   ├── hemibrain/          # new_cell_types, new_ALLNs, hemibrain_1-1_ROI_mapping, glomerulus_names
│   ├── flywire/            # FBbt_ID-cell_type, neuropil_map, superclasses, lineage_map,
│   │                       #   + gitignored: Supplemental_file1_neuron_annotations.tsv, *.feather
│   ├── male_cns/           # new_types, broad_type_map
│   └── optic_lobe/         # new_types, broad_type_map, OL_ROI_mapping
├── fetch/                  # opt-in neuPrint/FlyWire fetch scripts
│   ├── neuprint_common.py
│   └── fetch_{hemibrain,male_cns,optic_lobe,flywire_neuropils}.py
├── data/                   # evidence caches (gitignored) + PROVENANCE.tsv (tracked)
├── builds/                 # offline per-connectome row generators (no network)
│   └── build_{manc,hemibrain_cells,hemibrain_allns,flywire,male_cns,optic_lobe}.py
├── templates/              # gitignored cache of the six generated native templates
│                           #   (EM-<connectome>.tsv) — see "Template cache" below
└── README.md
```

Cross-dataset FBbt mappings are read from the `connectome-curation` repo (a
sibling of this repo: `datasets/<connectome>/resources/…`) via
`EM_common.curation_path`. The male-CNS region mapping
(`EM_neuropils/male-cns_regions.tsv`) is read from the in-repo `EM_neuropils`
project.

## Build

`build_EM_neurons.py` runs the six `builds/build_*.py` row generators,
re-expresses every connectome's output on the one `EM_unified.UNIFIED_HEADER`
schema (RO CURIEs throughout, so **no `robot template --input` is needed**),
keeps only the FBbt ids in `registry/EM_neuron_registry.tsv`, appends the ROBOT
issue-#1105 TYPE rows once, and writes a single template that the Makefile turns
into `EM_neurons.owl` with one `robot template`.

The **normal / release build** uses the committed `components/EM_neurons.owl`
and needs none of this.

### ODK setup

All the goals below run in the ODK container via `sh run.sh make <goal>` from
`src/ontology`. Two things from outside this repo have to be passed into the
container, which you set up once in your own `src/ontology/run.sh.conf`
(gitignored; `run.sh` reads it):

```sh
# Mount the sibling connectome-curation repo (read by refresh-EM-templates,
# refresh-EM-registry and refresh-EM-synonyms).
[ -d ../../../connectome-curation ] && \
    ODK_BINDS="$(cd ../../../connectome-curation && pwd):/connectome-curation"
# Pass NEUPRINT_TOKEN from your shell into the container (for refresh-EM-data).
ODK_DOCKER_OPTIONS="-e NEUPRINT_TOKEN"
```

Goals that need `connectome-curation` stop with an error if it isn't mounted.

### Regenerating

| Goal (`sh run.sh make …`) | What it does | When |
|---|---|---|
| `refresh-EM-data` | Re-fetches the neuPrint evidence caches (hemibrain v1.2.1, male-CNS v1.0, optic lobe v1.1) into `data/` and updates `data/PROVENANCE.tsv`. Needs network and `NEUPRINT_TOKEN` exported in your shell. Installs `neuprint-python` into `tmp/EM-fetch-pylib` the first time. | New connectome data |
| `refresh-EM-templates` | Recomputes the template cache (slow; see below). Needs `tmp/fbbt-merged.db` (run a normal build first if it is missing). | After new data or build-logic changes |
| `refresh-EM-registry` | Rebuilds `registry/EM_neuron_registry.tsv` from the template cache, the `sources/` id-lists and the curation mappings. | After adding terms |
| `refresh-EM-neurons` | Regenerates `components/EM_neurons.owl` from the cache + registry (fast). | After any of the above, or a registry edit |
| `refresh-EM-synonyms` | Regenerates the `EM_synonyms.owl` release asset (see below). | After curation-mapping changes |

To **add** terms, add them to the relevant `sources/<connectome>/` id-list, then
run `refresh-EM-templates`, `refresh-EM-registry` and `refresh-EM-neurons`. To **remove** one (e.g. when moving it to
`fbbt-edit.obo`), use `/move-to-edit`, which deletes its registry row, then
rebuild the component.

Two inputs have no make goal. MANC's typing data is committed
(`sources/manc/typing_info.tsv`), so it needs no fetch. The FlyWire
neuropil-volume cache (`data/flywire_neuropil_volumes.tsv`) comes from
`fetch/fetch_flywire_neuropils.py`, which needs `fafbseg`. `fafbseg` can't be
installed in the ODK image on ARM machines, as one of its dependencies needs a
Rust compiler. FAFB v783 is a fixed release, so the cache only needs fetching
once; run the script outside the container with `pip install fafbseg`.

### FlyWire source files (not reproducible yet)

The FlyWire and hemibrain builds also read three gitignored files in
`sources/flywire/` that no goal fetches, so a from-scratch rebuild currently
needs a curator who already has them:

- `Supplemental_file1_neuron_annotations.tsv`: from
  [flyconnectome/flywire_annotations](https://github.com/flyconnectome/flywire_annotations/tree/main/supplemental_files).
  The copy in use matches upstream commit
  [`c294fba`](https://raw.githubusercontent.com/flyconnectome/flywire_annotations/c294fba426f5abe861289bdc1171188026646b04/supplemental_files/Supplemental_file1_neuron_annotations.tsv)
  (2024-07-30). Upstream has changed a lot since, so updating to a newer
  version would change the generated terms and needs checking first.
- `per_neuron_neuropilv5_filtered_count_{pre,post}_783.feather`: per-neuron
  synapse counts per neuropil. Not publicly available as files, but they could
  in principle be regenerated from the public FAFB v783 Codex data at
  `gs://flywire-data/codex/data/fafb/783`
  ([console](https://console.cloud.google.com/storage/browser/flywire-data/codex/data/fafb/783)).

## Template cache

The six connectome row generators are slow (FlyWire's per-neuron soma
positioning alone takes 10+ minutes), so their native templates are **cached**
under `templates/EM-<connectome>.tsv` (gitignored, per curator).
`build_EM_neurons.py` reads the cache and computes only what is missing, so
rebuilding `EM_neurons.owl` after a registry edit is fast and needs neither the
evidence caches nor `tmp/fbbt-merged.db`.

`refresh-EM-templates` (`build_EM_neurons.py --refresh-cache`) is the only step
that needs the evidence caches and `tmp/fbbt-merged.db`. The cache is
deterministic apart from the order of values within some `SPLIT=|` columns,
which does not affect the axioms, so a refresh only changes the OWL when the
underlying data has changed.

## Evidence caches and provenance

The `data/*_roiinfo.tsv`, `data/*_hemilineage.tsv` and
`data/flywire_neuropil_volumes.tsv` caches are **gitignored** (like the FlyWire
feather files): they are only needed to regenerate the component and are kept
per curator. `data/PROVENANCE.tsv` **is** committed and records, for each cache,
the connectome dataset, version, source, fetch date and row count. The `fetch/`
scripts update it on every fetch (`record_provenance`).

Pinned versions: hemibrain v1.2.1, optic lobe v1.1, male-CNS v1.0, FlyWire FAFB
v783, MANC v1.2.1.

## Cross-dataset synonyms

The registry's `name_in_*` columns record each type's name in every other
dataset. These aren't emitted into `EM_neurons.owl`. The dataset-tagged synonyms
(with references) are published in the separate `EM_synonyms.owl` release
asset, generated by `../EM_synonyms/EM_synonym_template.py` from the same
`connectome-curation` mappings, with the same 1:1 filter. `EM_synonyms.owl` also
covers hand-curated `fbbt-edit.obo` terms, which is why it stays separate.

## Planned

- Reconcile connectome evidence across every connectome where a type appears
  (evidence merge).
- Make `EM_neurons.owl` fully rebuildable from scratch: add a pinned fetch for
  the FlyWire annotations file, and a way to regenerate the two `.feather`
  synapse-count files from the public Codex data (see
  "FlyWire source files" above).
