#!/usr/bin/env python3
"""Soma locations for MANC descending-neuron types, from the male CNS.

MANC has no brain, so its DN types have no soma location. The male CNS
annotates each DN with its MANC type (mancType) and its soma neuromere.
For every single (non-comma-lumped) MANC DN type whose male-CNS cells ALL
have their soma in the same brain region, this writes that region's cell
body rind as the soma location, which build_manc.py asserts on the type.
Male-CNS somaNeuromere codes: CG (protocerebrum: SMP, CL, FB, ... types),
DC (deutocerebrum: AL neurons), TC (tritocerebrum), and the gnathal
neuromeres MD, MX, LB plus GNG. A gnathal-ganglion soma, with the
cervical-connective fasciculation the build already asserts, classifies the
type as a 'descending neuron of the gnathal ganglion' (FBbt:00047516).

Opt-in: needs a neuPrint token. Dataset: male-cns:v1.0.

Usage:
    python3 fetch_manc_dn_soma.py --token <NEUPRINT_TOKEN>
Writes: EM_neurons/sources/manc/dn_soma_male_cns.tsv
"""

import argparse

import neuprint_common as nc

DATASET = "male-cns:v1.0"
GNG_CBR = ("FBbt:00100210", "cell body rind of adult gnathal ganglion")
SOMA_REGION = {"MD": GNG_CBR, "MX": GNG_CBR, "LB": GNG_CBR, "GNG": GNG_CBR,
               "CG": ("FBbt:00052048", "cell body rind of adult protocerebrum"),
               "DC": ("FBbt:00110410", "cell body rind of adult deutocerebrum"),
               "TC": ("FBbt:00052049", "cell body rind of adult tritocerebrum")}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--token", default=None, help="neuPrint token (or set NEUPRINT_TOKEN)")
    ap.add_argument("--dataset", default=DATASET, help=f"neuPrint dataset (default {DATASET})")
    args = ap.parse_args()

    client = nc.connect(args.dataset, nc.get_token(args.token))
    cells = client.fetch_custom(
        "MATCH (n:Neuron) WHERE n.mancType STARTS WITH 'DN' "
        "RETURN n.mancType AS manc_type, n.type AS mcns_type, n.somaNeuromere AS neuromere")
    cells = cells[~cells["manc_type"].str.contains(",")]
    rows = []
    for manc_type, g in cells.groupby("manc_type"):
        regions = {SOMA_REGION.get(n) for n in g["neuromere"].fillna("")}
        if len(regions) == 1 and None not in regions:
            [(soma_id, soma_name)] = regions
            rows.append({"manc_type": manc_type, "soma_FBbt_id": soma_id, "soma_FBbt_name": soma_name,
                         "male_cns_types": "|".join(sorted(set(g["mcns_type"]))), "n_male_cns_cells": len(g)})
    import pandas as pd
    out = pd.DataFrame(rows).sort_values("manc_type")
    path = nc.sources_path("manc", "dn_soma_male_cns.tsv")
    out.to_csv(path, sep="\t", index=False)
    print(f"Wrote {len(out)} MANC DN types with a brain soma region -> {path}")
    print(out["soma_FBbt_name"].value_counts().to_string())


if __name__ == "__main__":
    main()
