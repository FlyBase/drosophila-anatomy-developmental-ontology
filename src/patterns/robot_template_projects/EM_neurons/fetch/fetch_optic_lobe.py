#!/usr/bin/env python3
"""Fetch optic-lobe per-body roiInfo + hemilineage and cache for the offline build.

Opt-in: needs a neuPrint token. Reproduces the two queries in
optic_lobe/optic_lobe_neurons.ipynb (dataset optic-lobe:v1.1). Optic-lobe column
ROIs (containing '_col_') are kept in the raw cache and dropped in the build step
(matching the notebook).

Usage:
    python3 fetch_optic_lobe.py --token <NEUPRINT_TOKEN>

Writes: EM_neurons/data/optic_lobe_roiinfo.tsv
        EM_neurons/data/optic_lobe_hemilineage.tsv
"""

import argparse

import pandas as pd

import neuprint_common as nc

DATASET = "optic-lobe:v1.1"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--token", default=None, help="neuPrint token (or set NEUPRINT_TOKEN)")
    ap.add_argument("--dataset", default=DATASET, help=f"neuPrint dataset (default {DATASET})")
    args = ap.parse_args()

    cell_types = pd.read_csv(
        nc.project_path("optic_lobe", "new_types.tsv"),
        sep="\t", low_memory=False,
    )
    types = cell_types["OL_type"].tolist()

    client = nc.connect(args.dataset, nc.get_token(args.token))

    long = nc.fetch_roiinfo_long(client, types, include_instance=True)
    out_roi = nc.data_path("optic_lobe_roiinfo.tsv")
    long.to_csv(out_roi, sep="\t", index=False)
    nc.record_provenance("optic_lobe_roiinfo.tsv", args.dataset, "neuprint.janelia.org", len(long))
    print(f"Wrote {len(long)} (body, roi) rows for {long['type'].nunique()} types -> {out_roi}")

    # optic-lobe uses n.hemilineage (not itoleeHl/trumanHl)
    hl = nc.fetch_hemilineage(client, types, out_type_col="OL_type",
                              hl_expr="n.hemilineage", exists_expr="EXISTS(n.hemilineage)")
    out_hl = nc.data_path("optic_lobe_hemilineage.tsv")
    hl.to_csv(out_hl, sep="\t", index=False)
    nc.record_provenance("optic_lobe_hemilineage.tsv", args.dataset, "neuprint.janelia.org", len(hl))
    print(f"Wrote {len(hl)} hemilineage rows -> {out_hl}")


if __name__ == "__main__":
    main()
