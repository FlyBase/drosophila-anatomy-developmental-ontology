"""Unified EM-neuron ROBOT-template schema and per-connectome column mapping.

Phase 3 (Stage A) consolidates the six per-connectome ROBOT templates into a
single template with one header row. This module defines:

* ``UNIFIED_HEADER`` — the single ROBOT header (RO CURIEs throughout, so the
  merged build needs no ``--input`` for label resolution).
* ``COLUMN_MAPS`` — for each connectome, how its *native* template columns map
  onto the unified columns. Where several native columns are plain
  ``SC % [SPLIT=|]`` superclass assertions (e.g. hemibrain ``parent`` +
  ``hemilineage`` + ``arbor_type``) they are folded into the single unified
  ``parents`` column with ``|`` — an axiom-neutral rewrite (SubClassOf axioms
  are a set).
* ``to_unified`` / ``native_frames`` — read each connectome's native data rows
  and re-express them on the unified schema.

Reproduction guarantee: for every connectome, each native column maps to a
unified column whose ROBOT header string is byte-identical to the native one,
**except** the quoted relation labels (``'develops from'`` …) which become the
IRI-identical RO CURIEs (verified earlier as axiom-neutral). Cell values are
copied verbatim. So each connectome's contribution to the single template is
the same (header, value) set as its standalone template, and ``robot template``
produces the same axioms.

The six ``builds/build_*.py`` remain the tested, faithful row generators; this
module and ``build_EM_neurons.py`` drive them and unify their output.
"""

import io
import os
import re
import sys
from collections import OrderedDict

import pandas as pd

_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
_BUILDS_DIR = os.path.normpath(os.path.join(_LIB_DIR, "..", "builds"))
if _BUILDS_DIR not in sys.path:
    sys.path.insert(0, _BUILDS_DIR)

import EM_common as em  # noqa: E402


# ---------------------------------------------------------------------------
# Unified single-template header (RO CURIEs throughout -> no --input needed)
# ---------------------------------------------------------------------------
# Each ``>A`` axiom-annotation column immediately follows the ``A`` column it
# annotates, as ROBOT requires. Duplicate header strings across the three
# related-synonym slots are intentional and valid (male_cns/optic_lobe already
# ship three side-by-side hasRelatedSynonym columns): a row fills only the slots
# its connectome uses.
UNIFIED_HEADER = OrderedDict([
    ("ID", "ID"),
    ("TYPE", "TYPE"),
    ("obo_id", "A oboInOwl:id"),
    ("obo_namespace", "A oboInOwl:hasOBONamespace"),
    ("label", "A rdfs:label"),
    ("definition", "A IAO:0000115"),
    ("def_xref", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("comment", "A rdfs:comment"),
    ("created_by", "AI dc:contributor SPLIT=|"),
    ("creation_date", "AT dc:date^^xsd:dateTime"),
    # --- synonyms (distinct header signatures kept separate) ---------------
    ("exact_syn", "A oboInOwl:hasExactSynonym"),
    ("exact_syn_xref", ">A oboInOwl:hasDbXref"),
    ("exact_syn_split", "A oboInOwl:hasExactSynonym SPLIT=|"),
    ("exact_syn_split_xref", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("narrow_syn", "A oboInOwl:hasNarrowSynonym SPLIT=|"),
    ("narrow_syn_xref", ">A oboInOwl:hasDbXref"),
    ("related_syn_a", "A oboInOwl:hasRelatedSynonym SPLIT=|"),
    ("related_syn_a_xref", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("related_syn_b", "A oboInOwl:hasRelatedSynonym SPLIT=|"),
    ("related_syn_b_xref", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("related_syn_c", "A oboInOwl:hasRelatedSynonym SPLIT=|"),
    ("related_syn_c_xref", ">A oboInOwl:hasDbXref SPLIT=|"),
    # --- logic (RO CURIEs) -------------------------------------------------
    ("soma", "SC RO:0002100 some %"),
    ("parents", "SC % SPLIT=|"),
    ("develops_from", "SC RO:0002202 some %"),
    ("has_characteristic", "SC RO:0000053 some %"),
    ("fasciculates_with", "SC RO:0002101 some % SPLIT=|"),
    ("capable_of", "SC RO:0002215 some %"),
    ("synaptic_io", "SC RO:0013001 some % SPLIT=|"),
    ("receives_input", "SC RO:0013002 some % SPLIT=|"),
    ("sends_output", "SC RO:0013003 some % SPLIT=|"),
    ("sensory_dendrites", "SC RO:0013007 some % SPLIT=|"),
])

UNIFIED_COLS = list(UNIFIED_HEADER.keys())


# ---------------------------------------------------------------------------
# Per-connectome native -> unified column maps.
# Value is a native column name, or a list/tuple of native columns whose
# non-empty values are joined with "|" into the (SPLIT) unified column.
# ``TYPE`` is set to "owl:Class" for every row (see build_unified_rows), so it
# is not listed here even where the native template carried it.
# ---------------------------------------------------------------------------
COLUMN_MAPS = {
    "manc": {
        "obo_id": "obo_id", "obo_namespace": "obo_namespace",
        "label": "Label", "definition": "Definition", "def_xref": "Def_xrefs",
        "comment": "Comment", "created_by": "Creator", "creation_date": "Date",
        "exact_syn": "Exact_synonym", "exact_syn_xref": "Exact_syn_xref",
        "narrow_syn": "Narrow_synonyms", "narrow_syn_xref": "Narrow_syn_xref",
        "soma": "Soma", "parents": "Parents", "develops_from": "Lineage",
        "has_characteristic": "Laterality", "fasciculates_with": "Projection_bundles",
        "capable_of": "Neurotransmitter", "sends_output": "Presynapses",
        "receives_input": "Postsynapses", "sensory_dendrites": "Sens_dend",
    },
    "hb_cells": {
        "obo_id": "obo_id", "obo_namespace": "obo_namespace",
        "label": "label", "definition": "definition", "def_xref": "Xref_def",
        "comment": "comment", "created_by": "created_by", "creation_date": "creation_date",
        "exact_syn": "synonym", "exact_syn_xref": "syn_ref",
        "related_syn_a": "additional_synonym", "related_syn_a_xref": "additional_synonym_ref",
        "synaptic_io": "synapses", "receives_input": "inputs",
        "parents": ["parent", "hemilineage"], "develops_from": "neuroblast",
        "fasciculates_with": "tract", "sends_output": "outputs",
    },
    "hb_allns": {
        "obo_id": "obo_id", "obo_namespace": "obo_namespace",
        "label": "label", "definition": "definition", "def_xref": "Xref_def",
        "comment": "comment", "created_by": "created_by", "creation_date": "creation_date",
        "exact_syn": "synonym",
        "synaptic_io": "glomeruli", "receives_input": "inputs_AL", "sends_output": "outputs_AL",
        "parents": ["parent", "arbor_type", "hemilineage"], "develops_from": "neuroblast",
    },
    "male_cns": {
        "obo_id": "obo_id", "obo_namespace": "obo_namespace",
        "label": "label", "definition": "definition", "def_xref": "Xref_def",
        "comment": "comment", "created_by": "created_by", "creation_date": "creation_date",
        "related_syn_a": "hemibrain_type", "related_syn_a_xref": "hemibrain_ref",
        "related_syn_b": "flywire_type", "related_syn_b_xref": "flywire_ref",
        "related_syn_c": "manc_type", "related_syn_c_xref": "manc_ref",
        "parents": "parents", "capable_of": "NT",
        "receives_input": "inputs", "sends_output": "outputs",
        "has_characteristic": "laterality", "develops_from": "neuroblast",
    },
    "optic_lobe": {
        "obo_id": "obo_id", "obo_namespace": "obo_namespace",
        "label": "label", "definition": "definition", "def_xref": "Xref_def",
        "comment": "comment", "created_by": "created_by", "creation_date": "creation_date",
        "related_syn_a": "Matsliah_type", "related_syn_a_xref": "Matsliah_ref",
        "related_syn_b": "Schlegel_type", "related_syn_b_xref": "Schlegel_ref",
        "related_syn_c": "hemibrain_type", "related_syn_c_xref": "hemibrain_ref",
        "parents": "parents", "capable_of": "NT",
        "receives_input": "inputs", "sends_output": "outputs",
        "has_characteristic": "laterality", "develops_from": "neuroblast",
    },
    "flywire": {
        "obo_id": "obo_id", "obo_namespace": "obo_namespace",
        "label": "Label", "definition": "Definition", "def_xref": "Def_xrefs",
        "comment": "Comment", "created_by": "Creators", "creation_date": "Date",
        "related_syn_a": "RelatedSynonyms", "related_syn_a_xref": "RelatedSynonyms_xrefs",
        "exact_syn_split": "ExactSynonyms", "exact_syn_split_xref": "ExactSynonyms_xrefs",
        "soma": "Soma", "parents": "Parents", "develops_from": "Lineage",
        "has_characteristic": "Bilateral", "capable_of": "Neurotransmitter",
        "sends_output": "Presynapses", "receives_input": "Postsynapses",
    },
}

CONNECTOMES = list(COLUMN_MAPS.keys())

_FBBT_ID_RE = re.compile(r"^FBbt:\d+$")


def _blank(v):
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    return str(v).strip() == ""


def _join(values):
    parts = [str(v).strip() for v in values if not _blank(v)]
    return "|".join(parts)


def data_rows(native_df):
    """Return only the real term rows of a native template DataFrame.

    Excludes the ROBOT header row (obo_id == 'A oboInOwl:id') and any ROBOT
    issue-#1105 TYPE-declaration rows (blank obo_id). Data rows are identified
    by an ``obo_id`` that is an FBbt CURIE.
    """
    obo = native_df["obo_id"].astype(str).str.strip()
    return native_df[obo.str.match(_FBBT_ID_RE)].copy()


def to_unified(native_df, connectome):
    """Re-express a connectome's native *data* rows on the unified schema."""
    if connectome not in COLUMN_MAPS:
        raise KeyError(f"Unknown connectome: {connectome}")
    src = data_rows(native_df).reset_index(drop=True)
    out = pd.DataFrame("", index=range(len(src)), columns=UNIFIED_COLS)
    out["TYPE"] = "owl:Class"
    for unified_col, spec in COLUMN_MAPS[connectome].items():
        if isinstance(spec, (list, tuple)):
            out[unified_col] = [
                _join(vals) for vals in zip(*[src[c] for c in spec])
            ]
        else:
            out[unified_col] = [("" if _blank(v) else str(v)) for v in src[spec]]
    out["ID"] = [str(v).strip() for v in src["ID"]]
    out["defining_connectome"] = connectome
    return out


def _as_str_frame(df):
    """Round-trip a build_template() DataFrame through TSV so its cell values
    match exactly what ROBOT would read (NaN -> '', consistent str dtype)."""
    buf = io.StringIO()
    df.to_csv(buf, sep="\t", index=False)
    buf.seek(0)
    return pd.read_csv(buf, sep="\t", dtype=str, keep_default_na=False)


def native_frames(db_path, from_tsvs=None):
    """Return ``{connectome: native_str_DataFrame}`` for all six connectomes.

    ``from_tsvs``: directory of pre-built native templates named
    ``EM-<key>.tsv`` (dev fast-path; keys: manc, hb-allns, hb-cells, flywire,
    male-cns, optic-lobe). Otherwise the six ``builds/build_*.py`` are imported
    and run (offline, from committed data + evidence caches).
    """
    file_key = {"manc": "EM-manc", "hb_allns": "EM-hb-allns", "hb_cells": "EM-hb-cells",
                "flywire": "EM-flywire", "male_cns": "EM-male-cns", "optic_lobe": "EM-optic-lobe"}
    if from_tsvs:
        return {c: pd.read_csv(os.path.join(from_tsvs, file_key[c] + ".tsv"),
                               sep="\t", dtype=str, keep_default_na=False)
                for c in CONNECTOMES}

    import build_manc, build_hemibrain_allns, build_hemibrain_cells
    import build_flywire, build_male_cns, build_optic_lobe
    return {
        "manc": _as_str_frame(build_manc.build_template()),
        "hb_allns": _as_str_frame(build_hemibrain_allns.build_template()),
        "hb_cells": _as_str_frame(build_hemibrain_cells.build_template()),
        "flywire": _as_str_frame(build_flywire.build_template("both")),
        "male_cns": _as_str_frame(build_male_cns.build_template(db_path)),
        "optic_lobe": _as_str_frame(build_optic_lobe.build_template(db_path)),
    }


def unified_data_frame(db_path, from_tsvs=None):
    """Collect all connectomes' data rows on the unified schema (concatenated,
    with a ``defining_connectome`` column). No header / #1105 rows added."""
    frames = native_frames(db_path, from_tsvs=from_tsvs)
    return pd.concat([to_unified(frames[c], c) for c in CONNECTOMES], ignore_index=True)


def header_row():
    return pd.DataFrame.from_records([UNIFIED_HEADER], columns=UNIFIED_COLS)
