"""Shared helpers for EM connectome neuron-term generation.

This module consolidates logic that was previously copy-pasted across the
per-connectome generator notebooks (flywire, hemibrain, manc, optic_lobe,
male_cns). It is deliberately dependency-light: only the OAK part-of pruner
needs an ontology adapter, which the caller supplies.

Scope: EM-connectome neuron terms only. VNC_neurons (Feng/Ehrhardt) is NOT
EM-derived and is out of scope for this pipeline.

Usage from a build script in the parent folder::

    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
    import EM_common as em
"""

import re
from collections import OrderedDict

import pandas as pd


# ---------------------------------------------------------------------------
# Neurotransmitters
# ---------------------------------------------------------------------------
# Canonical neurotransmitter name -> GO "neurotransmitter secretion" CV.
# Superset of the (divergent) dicts previously kept in flywire_neurons.ipynb
# (6 entries), male_cns_neurons.ipynb and optic_lobe_neurons.ipynb (3 each).
# Lookup is case-insensitive so both 'gaba' (flywire) and 'GABA' (optic_lobe)
# resolve.
NT_TO_GO = {
    "acetylcholine": "GO:0014055",
    "glutamate": "GO:0061535",
    "gaba": "GO:0061534",
    "serotonin": "GO:0060096",
    "dopamine": "GO:0061527",
    "octopamine": "GO:0061540",
}


def neurotransmitter_go(name):
    """Return the GO CV for a neurotransmitter name, or '' if unknown/blank.

    Case-insensitive; tolerates None/NaN.
    """
    if name is None:
        return ""
    try:
        if pd.isna(name):
            return ""
    except (TypeError, ValueError):
        pass
    return NT_TO_GO.get(str(name).strip().lower(), "")


# ---------------------------------------------------------------------------
# Cell body rind (soma location) defaults
# ---------------------------------------------------------------------------
# The full neuropil -> cell-body-rind resolution is connectome-specific and
# stays in the individual build scripts; these are the shared fall-back IDs
# they all reference.
CBR_ADULT_BRAIN = "FBbt:00003625"  # adult brain cell body rind (default)
CBR_PERIPHERY = "FBbt:00005892"    # peripheral nervous system (sensory somata)


# ---------------------------------------------------------------------------
# Laterality (PATO)
# ---------------------------------------------------------------------------
PATO_BILATERAL = "PATO:0000618"    # bilateral (used when any contralateral arbor)
PATO_UNILATERAL = "PATO:0000634"   # unilateral


def laterality_pato(has_contralateral):
    """Return PATO_BILATERAL if the type has any contralateral projection.

    Mirrors the shared `'contralateral' in definition -> PATO:0000618` rule.
    Returns '' otherwise so it can drop straight into a template cell.
    """
    return PATO_BILATERAL if has_contralateral else ""


# ---------------------------------------------------------------------------
# name_lister: "a", "a and b", "a, b and c"
# ---------------------------------------------------------------------------
def name_lister(names, sort=False):
    """Join a list of names into an English list ("a, b and c").

    Returns False for an empty list (preserving the behaviour the callers rely
    on). ``sort=True`` reproduces the manc/optic-lobe variant that sorts first;
    ``sort=False`` (default) reproduces the unsorted variant.
    """
    names = list(names)
    if sort:
        names = sorted(names)
    if len(names) < 1:
        return False
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


# ---------------------------------------------------------------------------
# ROBOT issue #1105 workaround: declare TYPE for every referenced CURIE
# ---------------------------------------------------------------------------
# See https://github.com/ontodev/robot/issues/1105 . Every FBbt/GO/PATO/RO
# CURIE used in a class-expression column must appear as its own row with an
# explicit TYPE, or robot template drops axioms.
CURIE_RE = re.compile(r"\b(?:FBbt|GO|PATO|RO):\d+\b")


def extract_uris(text):
    """Return all FBbt/GO/PATO/RO CURIEs found in a cell value."""
    return CURIE_RE.findall(str(text))


def referenced_curies(template, id_col="ID"):
    """Collect the distinct FBbt/GO/PATO/RO CURIEs referenced anywhere in a
    template DataFrame (excluding the ID column itself)."""
    curies = set()
    for column in template.columns:
        if column == id_col:
            continue
        for value in template[column].dropna():
            curies.update(extract_uris(value))
    return sorted(curies)


def type_rows_for_referenced_curies(template, id_col="ID", type_col="TYPE"):
    """Build the extra ID/TYPE rows needed for the #1105 workaround.

    RO:* CURIEs are declared owl:ObjectProperty; everything else owl:Class.
    Returned rows have the same columns as ``template`` (others blank). Callers
    append these to their template before writing it out.
    """
    rows = []
    for curie in referenced_curies(template, id_col=id_col):
        row = OrderedDict((c, "") for c in template.columns)
        row[id_col] = curie
        row[type_col] = "owl:ObjectProperty" if curie.startswith("RO:") else "owl:Class"
        rows.append(row)
    return pd.DataFrame.from_records(rows, columns=list(template.columns))


# ---------------------------------------------------------------------------
# ROBOT template header construction
# ---------------------------------------------------------------------------
def build_template_header(column_spec):
    """Turn an ordered {column: robot-template-string} mapping into the ROBOT
    header DataFrame (a single row whose values are the template strings).

    Example::

        spec = OrderedDict([("ID", "ID"), ("TYPE", "TYPE"),
                            ("label", "A rdfs:label"),
                            ("parents", "SC % SPLIT=|")])
        template = build_template_header(spec)
    """
    spec = OrderedDict(column_spec)
    return pd.DataFrame.from_records([spec], columns=list(spec.keys()))


# ---------------------------------------------------------------------------
# Side / laterality helpers (shared by optic_lobe and male_cns generators)
# ---------------------------------------------------------------------------
_R_SIDE = re.compile(r"[_(]R[_)]?")
_L_SIDE = re.compile(r"[_(]L[_)]?")


def find_side(label):
    """right/left/no_side from a neuprint instance or ROI name (e.g. 'ME(R)')."""
    if label is None:
        return "no_side"
    if _R_SIDE.search(str(label)):
        return "right"
    if _L_SIDE.search(str(label)):
        return "left"
    return "no_side"


def laterality(cell_side, np_side):
    """ipsilateral / contralateral / no_laterality from a soma side and ROI side."""
    if "no_side" not in (cell_side, np_side):
        return "ipsilateral" if cell_side == np_side else "contralateral"
    return "no_laterality"


def laterality_connectivity(cache, raw_roi_map):
    """Reconstruct the notebook's per-body, per-side connectivity table with the
    class-level consistency filter, for the laterality-aware generators.

    The notebook does ROIs.apply(pd.Series).stack(future_stack=True) then
    .apply(pd.Series).fillna(0), which materialises a ZERO for every
    (body, side, region) pair a body lacks; the later groupby(type,laterality,
    ROI).min() therefore drops any (laterality, region) not present in EVERY
    body of the type. Our cache stores only present pairs, so we rebuild the
    full (body x region) grid per type (0-filled) before deriving laterality.

    ``cache`` columns: type, bodyId, instance, roi, pre, post (roi = neuprint
    ROI name, e.g. 'ME(R)'). ``raw_roi_map`` maps roi -> FBbt id. Returns a
    DataFrame indexed by (type, laterality, ROI) with pre/post (min across all
    bodies), both-zero rows dropped.
    """
    df = cache.copy()
    df["cell_side"] = df["instance"].map(find_side)
    # Dataset-wide roi universe (mapped rois only): every body is 0-filled for
    # every roi seen anywhere in the cache -- including BOTH side-variants of a
    # region -- so the laterality-aware min drops a (laterality, region) unless
    # every body carries its own-side variant of it. Using a per-type union
    # would omit the cross-side zeros and weaken the filter.
    mapped = df[df["roi"].isin(raw_roi_map.keys())]
    global_rois = pd.DataFrame({"roi": mapped["roi"].drop_duplicates().tolist()})
    bodies = df[["type", "bodyId", "cell_side"]].drop_duplicates()
    grid = bodies.merge(global_rois, how="cross")  # (type, body) x every mapped roi
    grid = grid.merge(df[["type", "bodyId", "roi", "pre", "post"]],
                      on=["type", "bodyId", "roi"], how="left")
    grid["pre"] = grid["pre"].fillna(0)
    grid["post"] = grid["post"].fillna(0)
    grid["ROI"] = grid["roi"].map(raw_roi_map)
    grid["np_side"] = grid["roi"].map(find_side)
    grid["laterality"] = [laterality(c, n) for c, n in zip(grid["cell_side"], grid["np_side"])]
    body_ct = grid.groupby(["type", "bodyId", "laterality", "ROI"], as_index=False).agg(
        post=("post", "max"), pre=("pre", "max"))
    type_ct = body_ct.groupby(["type", "laterality", "ROI"]).agg(
        post=("post", "min"), pre=("pre", "min"))
    type_ct = type_ct[~(type_ct["post"].eq(0) & type_ct["pre"].eq(0))]
    return type_ct


# ---------------------------------------------------------------------------
# OAK part-of redundancy pruning (generalised from male_cns / optic_lobe)
# ---------------------------------------------------------------------------
def drop_redundant_part_of(term_list, descendants_map):
    """Drop terms that are part-of ancestors of another term in the list.

    ``descendants_map`` maps an FBbt id to the set/list of its part-of
    descendants (BFO:0000050, entailed). A term is kept unless another term in
    the list is one of its descendants (i.e. keep the most specific regions).
    """
    terms = list(dict.fromkeys(term_list))  # de-dup, preserve order
    kept = []
    for t in terms:
        descendants = set(descendants_map.get(t, ()))
        if not (set(terms) - {t}) & descendants:
            kept.append(t)
    return kept


if __name__ == "__main__":
    # Lightweight self-checks (the "unit checks" referenced in the plan).
    assert name_lister([]) is False
    assert name_lister(["a"]) == "a"
    assert name_lister(["a", "b"]) == "a and b"
    assert name_lister(["b", "a", "c"]) == "b, a and c"
    assert name_lister(["b", "a", "c"], sort=True) == "a, b and c"
    assert neurotransmitter_go("GABA") == "GO:0061534"
    assert neurotransmitter_go("gaba") == "GO:0061534"
    assert neurotransmitter_go("") == ""
    assert neurotransmitter_go(None) == ""
    assert extract_uris("SC RO:0002100 some FBbt:00003625") == ["RO:0002100", "FBbt:00003625"]
    assert laterality_pato(True) == PATO_BILATERAL
    assert laterality_pato(False) == ""
    # part-of pruning: if 00003748 is part of 00003701, keep the specific one.
    dmap = {"FBbt:00003701": ["FBbt:00003748"]}
    assert drop_redundant_part_of(["FBbt:00003701", "FBbt:00003748"], dmap) == ["FBbt:00003748"]
    print("EM_common self-checks passed")
