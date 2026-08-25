#!/usr/bin/env python3
"""Build the EM-neuron registry (Phase 3, Stage A).

The registry (``EM_neuron_registry.tsv``) is the single, committed list of every
EM-minted FBbt neuron id — one row per id — and the ``move-to-edit`` removal
target: ``build_EM_neurons.py`` emits only ids present here, so deleting a row
drops its term on the next rebuild.

Each row records:
* ``FBbt_id`` / ``label`` / ``defining_connectome`` — taken from the actual
  output of the six ``builds/build_*.py`` (via ``EM_unified``), so the registry
  id set is guaranteed to equal the build output (no drift). ``defining_connectome``
  is the generator that mints the id (a hemibrain-block id is ``flywire`` when
  FlyWire re-defines it, else ``hemibrain``).
* ``type_name`` — the defining connectome's own name for the type, from its
  ``sources/<c>/`` id-list.
* ``name_in_<dataset>`` — every dataset's 1:1 name for the id, inverted from the
  six ``../connectome-curation`` bridges exactly as ``EM_synonyms`` does
  (``specificity`` blank, single FBbt id). Recorded as the consolidated identity
  record; **not** emitted into terms in Stage A (that is Stage B).

Usage:
    python3 build_registry.py [--out EM_neuron_registry.tsv]
                              [--db .../fbbt-merged.db] [--from-tsvs DIR]
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import EM_common as em      # noqa: E402
import EM_unified as u      # noqa: E402

# collector key -> human-readable defining_connectome label
DEFINING_LABEL = {
    "manc": "manc", "hb_cells": "hemibrain", "hb_allns": "hemibrain_allns",
    "flywire": "flywire", "male_cns": "male_cns", "optic_lobe": "optic_lobe",
}

NAME_IN_COLS = ["name_in_flywire", "name_in_hemibrain", "name_in_manc",
                "name_in_optic_lobe", "name_in_male_cns", "name_in_banc"]

# ../connectome-curation bridge -> (curation dataset dir, filename, type-name column,
#                                   registry name_in_* column)
BRIDGES = [
    ("optic_lobe", "OL_FBbt_mapping.tsv", "OL_type", "name_in_optic_lobe"),
    ("manc", "manc_cell_type_fbbt_mapping.tsv", "type", "name_in_manc"),
    ("flywire", "flywire_fbbt_mapping.tsv", "primary_type", "name_in_flywire"),
    ("hemibrain", "hemibrain_1-2_type_mapping.tsv", "np_type", "name_in_hemibrain"),
    ("male_cns", "all_male-cns_FBbt.tsv", "type", "name_in_male_cns"),
    ("banc", "all_banc_FBbt.tsv", "type", "name_in_banc"),
]


def _src(*parts):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "sources", *parts))


def type_name_map():
    """FBbt_id -> the defining connectome's own type name (from source lists).
    IDs are disjoint across connectomes, so one flat dict is unambiguous."""
    m = {}

    def add(df, id_col, name_col):
        for _id, name in zip(df[id_col], df[name_col]):
            if isinstance(_id, str) and _id.startswith("FBbt:"):
                m[_id] = name

    add(pd.read_csv(_src("manc", "new_cell_FBbt_ids.tsv"), sep="\t", dtype=str), "FBbt_id", "type")
    add(pd.read_csv(_src("hemibrain", "new_ALLNs.tsv"), sep="\t", dtype=str), "FBbt_id", "np_type")
    add(pd.read_csv(_src("hemibrain", "new_cell_types.tsv"), sep="\t", dtype=str), "FBbt_id", "np_type")
    add(pd.read_csv(_src("flywire", "FBbt_ID-cell_type.tsv"), sep="\t", dtype=str), "FBbt_id", "cell_type")
    add(pd.read_csv(_src("male_cns", "new_types.tsv"), sep="\t", dtype=str), "FBbt_id", "mcns_type")
    add(pd.read_csv(_src("optic_lobe", "new_types.tsv"), sep="\t", dtype=str), "FBbt_id", "OL_type")
    return m


def name_in_maps():
    """{registry name_in_* column: {FBbt_id: 'name1|name2|...'}} from the bridges."""
    out = {}
    for dataset, fname, syn_col, reg_col in BRIDGES:
        df = pd.read_csv(em.curation_path(dataset, fname), sep="\t", dtype="str")
        df = df[["FBbt_id", syn_col, "specificity"]].drop_duplicates()
        # 1:1 mappings only (specificity blank, single FBbt id) — as EM_synonyms.
        df = df[df["FBbt_id"].notna() & df["specificity"].isna() & df[syn_col].notna()]
        df = df[~df["FBbt_id"].str.contains("|", regex=False)]
        grouped = (df.groupby("FBbt_id")[syn_col]
                   .apply(lambda s: "|".join(dict.fromkeys(s))))
        out[reg_col] = grouped.to_dict()
    return out


def build(db_path, from_tsvs=None):
    uni = u.unified_data_frame(db_path, from_tsvs=from_tsvs)
    reg = uni[["ID", "label", "defining_connectome"]].drop_duplicates("ID").copy()
    reg = reg.rename(columns={"ID": "FBbt_id"})
    reg["defining_connectome"] = reg["defining_connectome"].map(DEFINING_LABEL)

    tn = type_name_map()
    reg["type_name"] = reg["FBbt_id"].map(tn).fillna("")

    for reg_col, id2name in name_in_maps().items():
        reg[reg_col] = reg["FBbt_id"].map(id2name).fillna("")

    reg = reg[["FBbt_id", "label", "defining_connectome", "type_name"] + NAME_IN_COLS]
    reg = reg.sort_values(["defining_connectome", "FBbt_id"]).reset_index(drop=True)
    return reg


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--out", default=os.path.join(here, "EM_neuron_registry.tsv"))
    ap.add_argument("--db", default=os.path.normpath(
        os.path.join(here, "..", "..", "..", "..", "ontology", "tmp", "fbbt-merged.db")))
    ap.add_argument("--from-tsvs", default=None, help="dev: dir of pre-built native templates")
    args = ap.parse_args()
    reg = build(args.db, from_tsvs=args.from_tsvs)
    reg.to_csv(args.out, sep="\t", index=False)
    print(f"Wrote {len(reg)} registry rows -> {args.out}")
    print(reg["defining_connectome"].value_counts().to_string())


if __name__ == "__main__":
    main()
