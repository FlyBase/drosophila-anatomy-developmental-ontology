#!/usr/bin/env python3
"""Fetch male-CNS per-body roiInfo + hemilineage and cache for the offline build.

Opt-in: needs a neuPrint token. Reproduces the two queries in
male_cns_neurons/male_cns_neurons.ipynb.

Dataset version: pinned to 'male-cns:v0.9' for now, to reproduce the current
committed male_cns_neurons.owl exactly. Updating to 'male-cns:v1.0' is a planned
follow-up (run with --dataset male-cns:v1.0) once the content refresh has been
reviewed.

Usage:
    python3 fetch_male_cns.py --token <NEUPRINT_TOKEN> [--dataset male-cns:v1.0]

Writes: EM_neurons/data/male_cns_roiinfo.tsv
        EM_neurons/data/male_cns_hemilineage.tsv
"""

import argparse

import pandas as pd

import neuprint_common as nc

DATASET = "male-cns:v0.9"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--token", default=None, help="neuPrint token (or set NEUPRINT_TOKEN)")
    ap.add_argument("--dataset", default=DATASET, help=f"neuPrint dataset (default {DATASET})")
    args = ap.parse_args()

    cell_types = pd.read_csv(
        nc.project_path("male_cns_neurons", "new_types.tsv"),
        sep="\t", low_memory=False,
    )
    types = cell_types["mcns_type"].tolist()

    client = nc.connect(args.dataset, nc.get_token(args.token))

    long = nc.fetch_roiinfo_long(client, types, include_instance=True)
    out_roi = nc.data_path("male_cns_roiinfo.tsv")
    long.to_csv(out_roi, sep="\t", index=False)
    nc.record_provenance("male_cns_roiinfo.tsv", args.dataset, "neuprint.janelia.org", len(long))
    print(f"Wrote {len(long)} (body, roi) rows for {long['type'].nunique()} types -> {out_roi}")

    hl = nc.fetch_hemilineage(client, types, out_type_col="mcns_type")
    out_hl = nc.data_path("male_cns_hemilineage.tsv")
    hl.to_csv(out_hl, sep="\t", index=False)
    nc.record_provenance("male_cns_hemilineage.tsv", args.dataset, "neuprint.janelia.org", len(hl))
    print(f"Wrote {len(hl)} hemilineage rows -> {out_hl}")


if __name__ == "__main__":
    main()
