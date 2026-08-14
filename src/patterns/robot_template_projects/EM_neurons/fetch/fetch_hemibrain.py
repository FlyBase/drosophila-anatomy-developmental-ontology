#!/usr/bin/env python3
"""Fetch hemibrain per-body roiInfo and cache it for the offline build.

Opt-in: needs a neuPrint token. Reproduces the query in
hemibrain_new_types/update_new_types.ipynb (dataset hemibrain:v1.2.1). Fetches
connectivity for ALL np_types in new_cell_types.tsv (the FlyWire overlap filter
is applied later, in the build step, so the cache is independent of it).

Usage:
    python3 fetch_hemibrain.py --token <NEUPRINT_TOKEN>
    # or: NEUPRINT_TOKEN=... python3 fetch_hemibrain.py

Writes: EM_neurons/data/hemibrain_roiinfo.tsv
"""

import argparse

import pandas as pd

import neuprint_common as nc

DATASET = "hemibrain:v1.2.1"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--token", default=None, help="neuPrint token (or set NEUPRINT_TOKEN)")
    ap.add_argument("--dataset", default=DATASET, help=f"neuPrint dataset (default {DATASET})")
    args = ap.parse_args()

    cell_types = pd.read_csv(
        nc.sources_path("hemibrain", "new_cell_types.tsv"),
        sep="\t", dtype="str", na_filter=False,
    )
    types = cell_types["np_type"].tolist()

    client = nc.connect(args.dataset, nc.get_token(args.token))
    long = nc.fetch_roiinfo_long(client, types, include_instance=False)

    out = nc.data_path("hemibrain_roiinfo.tsv")
    long.to_csv(out, sep="\t", index=False)
    nc.record_provenance("hemibrain_roiinfo.tsv", args.dataset, "neuprint.janelia.org", len(long))
    print(f"Wrote {len(long)} (body, roi) rows for {long['type'].nunique()} types -> {out}")


if __name__ == "__main__":
    main()
