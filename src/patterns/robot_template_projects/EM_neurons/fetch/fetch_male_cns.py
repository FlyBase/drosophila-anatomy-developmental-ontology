#!/usr/bin/env python3
"""Fetch male-CNS per-body roiInfo + hemilineage and cache for the offline build.

Opt-in: needs a neuPrint token.

Dataset version: 'male-cns:v1.0'. Override with --dataset.

Usage:
    python3 fetch_male_cns.py --token <NEUPRINT_TOKEN> [--dataset male-cns:v0.9]

Writes: EM_neurons/data/male_cns_roiinfo.tsv
        EM_neurons/data/male_cns_hemilineage.tsv
"""

import argparse

import pandas as pd

import neuprint_common as nc

DATASET = "male-cns:v1.0"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--token", default=None, help="neuPrint token (or set NEUPRINT_TOKEN)")
    ap.add_argument("--dataset", default=DATASET, help=f"neuPrint dataset (default {DATASET})")
    args = ap.parse_args()

    cell_types = pd.read_csv(
        nc.sources_path("male_cns", "new_types.tsv"),
        sep="\t", low_memory=False,
    )
    # A row can group several male-CNS types under one term (mcns_members,
    # '|'-separated); their bodies are cached under the row's mcns_type.
    members = cell_types["mcns_members"] if "mcns_members" in cell_types else [None] * len(cell_types)
    member_of = {}
    for row_type, row_members in zip(cell_types["mcns_type"], members):
        for m in (row_members.split("|") if isinstance(row_members, str) and row_members else [row_type]):
            member_of[m] = row_type
    types = sorted(member_of)

    client = nc.connect(args.dataset, nc.get_token(args.token))

    long = nc.fetch_roiinfo_long(client, types, include_instance=True)
    long["type"] = long["type"].map(member_of)
    out_roi = nc.data_path("male_cns_roiinfo.tsv")
    long.to_csv(out_roi, sep="\t", index=False)
    nc.record_provenance("male_cns_roiinfo.tsv", args.dataset, "neuprint.janelia.org", len(long))
    print(f"Wrote {len(long)} (body, roi) rows for {long['type'].nunique()} types -> {out_roi}")

    hl = nc.fetch_hemilineage(client, types, out_type_col="mcns_type")
    hl["mcns_type"] = hl["mcns_type"].map(member_of)
    hl = hl.drop_duplicates()
    out_hl = nc.data_path("male_cns_hemilineage.tsv")
    hl.to_csv(out_hl, sep="\t", index=False)
    nc.record_provenance("male_cns_hemilineage.tsv", args.dataset, "neuprint.janelia.org", len(hl))
    print(f"Wrote {len(hl)} hemilineage rows -> {out_hl}")


if __name__ == "__main__":
    main()
