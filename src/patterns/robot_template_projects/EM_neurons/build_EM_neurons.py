#!/usr/bin/env python3
"""Generate the single consolidated EM-neuron ROBOT template (offline).

Phase 3 (Stage A). Drives the six per-connectome row generators
(``builds/build_*.py``), re-expresses their output on the one
``EM_unified.UNIFIED_HEADER`` schema (RO CURIEs throughout, so ``robot
template`` needs no ``--input``), filters to the FBbt ids listed in the
committed registry (``registry/EM_neuron_registry.tsv`` — the single ID source
and the ``move-to-edit`` removal target), appends the ROBOT issue-#1105 TYPE
rows once for the whole template, and writes one ``template.tsv``.

The Makefile then runs a single ``robot template`` (no merge, no ``--input``).

Usage:
    python3 build_EM_neurons.py --out template.tsv [--db .../fbbt-merged.db]
                                [--registry registry/EM_neuron_registry.tsv]
                                [--from-tsvs DIR]   # dev: reuse pre-built native TSVs
                                [--no-filter]       # dev: skip the registry filter
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import EM_common as em      # noqa: E402
import EM_unified as u      # noqa: E402


def _default_db():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "..", "ontology", "tmp", "fbbt-merged.db"))


def _default_registry():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "registry", "EM_neuron_registry.tsv")


def build(db_path, registry_path=None, from_tsvs=None, do_filter=True):
    rows = u.unified_data_frame(db_path, from_tsvs=from_tsvs)

    dup = rows["ID"][rows["ID"].duplicated()].unique()
    if len(dup):
        raise ValueError(f"Duplicate FBbt ids across connectomes: {list(dup)[:10]}")

    if do_filter and registry_path and os.path.exists(registry_path):
        registry = pd.read_csv(registry_path, sep="\t", dtype=str, keep_default_na=False)
        reg_ids = registry["FBbt_id"].tolist()
        reg_set, built_set = set(reg_ids), set(rows["ID"])
        only_reg = reg_set - built_set
        only_built = built_set - reg_set
        if only_reg:
            print(f"WARNING: {len(only_reg)} registry ids not produced by the builds "
                  f"(e.g. {sorted(only_reg)[:5]})", file=sys.stderr)
        if only_built:
            print(f"WARNING: {len(only_built)} built ids absent from the registry "
                  f"(e.g. {sorted(only_built)[:5]}); they will be DROPPED", file=sys.stderr)
        order = {i: n for n, i in enumerate(reg_ids)}
        rows = rows[rows["ID"].isin(reg_set)].copy()
        rows["_o"] = rows["ID"].map(order)
        rows = rows.sort_values("_o").drop(columns=["_o"])

    rows = rows.drop(columns=["defining_connectome"]).reset_index(drop=True)

    template = pd.concat([u.header_row(), rows], ignore_index=True)
    # ROBOT issue #1105: declare TYPE for every referenced CURIE (scans the
    # header row too, so the RO:* predicates are declared as ObjectProperties).
    template = pd.concat([template, em.type_rows_for_referenced_curies(template)],
                         ignore_index=True)
    return template


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="template.tsv")
    ap.add_argument("--db", default=_default_db(), help="path to fbbt-merged.db (OAK)")
    ap.add_argument("--registry", default=_default_registry())
    ap.add_argument("--from-tsvs", default=None, help="dev: dir of pre-built native templates")
    ap.add_argument("--no-filter", action="store_true", help="dev: skip registry filter")
    args = ap.parse_args()

    template = build(args.db, registry_path=args.registry,
                     from_tsvs=args.from_tsvs, do_filter=not args.no_filter)
    template.to_csv(args.out, sep="\t", index=False)
    n_terms = int((template["obo_id"].astype(str).str.match(u._FBBT_ID_RE)).sum())
    print(f"Wrote {len(template)} rows ({n_terms} terms) -> {args.out}")


if __name__ == "__main__":
    main()
