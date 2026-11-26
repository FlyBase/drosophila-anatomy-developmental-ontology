#!/usr/bin/env python3
"""Build the male-CNS neuron-term ROBOT template (offline).

Reads the male-CNS evidence caches (male_cns_roiinfo.tsv, male_cns_hemilineage.tsv,
from the neuPrint fetch step), curated maps, and the FlyWire lineage map. Uses
OAK against the built tmp/fbbt-merged.db for part-of redundancy pruning. The
class-level connectivity-consistency filter is applied by
EM_common.laterality_connectivity. No network/token.

NB: dataset pinned to male-cns:v1.0 via the cache (see fetch_male_cns.py).
Emits native quoted-label relation columns and no #1105 TYPE rows; the
consolidated build (`build_EM_neurons.py`) re-expresses these as RO CURIEs and
adds the #1105 rows for the whole template, so no `robot template --input` is
needed there. Standalone, this native template needs `--input` for the quoted
labels.

Usage:
    python3 build_male_cns.py [--out template.tsv] [--db ../../../ontology/tmp/fbbt-merged.db]
"""

import argparse
import json
import os
import re
import sys
from collections import OrderedDict

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import EM_common as em  # noqa: E402

CONNECTIVITY_THRESHOLD = 10
TRACT_RE = r"\bconnective\b|\bnerve\b(?! cord)"   # region names that are fibre tracts
NT_CVS = {"acetylcholine": "GO:0014055", "GABA": "GO:0061534", "glutamate": "GO:0061535",
          "dopamine": "GO:0061527", "serotonin": "GO:0060096", "octopamine": "GO:0061540",
          "tyramine": "GO:0061546"}
# Optional new_types.tsv columns: mcns_members ('|' male-CNS types grouped
# under one term), banc_type (BANC name, for citation), exclude_inputs /
# exclude_outputs ('|' FBbt region ids another connectome contradicts),
# exclude_hemilineage (TRUE to drop it), cross_check_comment (appended to the
# comment).
OPTIONAL_COLUMNS = ["mcns_members", "banc_type", "exclude_inputs", "exclude_outputs",
                    "exclude_hemilineage", "cross_check_comment"]


def _proj(*parts):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", *parts))


def _cache(name):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "data", name))


def _default_db():
    # builds/ -> EM_neurons -> robot_template_projects -> patterns -> src -> ontology/tmp
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "..", "..", "ontology", "tmp", "fbbt-merged.db"))

TEMPLATE_SEED = OrderedDict([
    ("ID", "ID"),
    ("obo_id", "A oboInOwl:id"), ("obo_namespace", "A oboInOwl:hasOBONamespace"),
    ("label", "A rdfs:label"), ("definition", "A IAO:0000115"),
    ("Xref_def", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("created_by", "AI dc:contributor"), ("creation_date", "AT dc:date^^xsd:dateTime"),
    ("hemibrain_type", "A oboInOwl:hasRelatedSynonym SPLIT=|"),
    ("hemibrain_ref", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("flywire_type", "A oboInOwl:hasRelatedSynonym SPLIT=|"),
    ("flywire_ref", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("manc_type", "A oboInOwl:hasRelatedSynonym SPLIT=|"),
    ("manc_ref", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("comment", "A rdfs:comment"),
    ("parents", "SC % SPLIT=|"),
    ("NT", "SC 'capable of' some %"),
    ("inputs", "SC 'receives synaptic input in region' some % SPLIT=|"),
    ("outputs", "SC 'sends synaptic output to region' some % SPLIT=|"),
    ("laterality", "SC 'has characteristic' some %"),
    ("neuroblast", "SC 'develops from' some %"),
])


def build_template(db_path):
    import numpy as np
    from oaklib import get_adapter

    cell_types = pd.read_csv(_proj("EM_neurons", "sources", "male_cns", "new_types.tsv"), sep="\t",
                             low_memory=False, index_col="mcns_type")
    parent_types = pd.read_csv(_proj("EM_neurons", "sources", "male_cns", "broad_type_map.tsv"), sep="\t",
                               low_memory=False, index_col="broad_type")
    # Optional curation columns (see sources/male_cns/README section in the
    # project README): cross-connectome exclusions and multi-type rows.
    for col in OPTIONAL_COLUMNS:
        if col not in cell_types:
            cell_types[col] = np.nan
    if "label_style" not in parent_types:
        parent_types["label_style"] = np.nan

    def _split(value):
        return [x for x in str(value).split("|") if x] if pd.notna(value) else []
    hemilineage_map = pd.read_csv(_proj("EM_neurons", "sources", "flywire", "lineage_map.tsv"), sep="\t", low_memory=False)
    # ROI->FBbt mapping from the shared EM_neuropils v1.0 region table (adult/
    # segment-specific terms; '-unspecified' catch-alls are left blank -> excluded,
    # which is lossless since they are part-of ancestors of the specific regions).
    mcns_rois = pd.read_csv(_proj("EM_neuropils", "male-cns_regions.tsv"), sep="\t", dtype=str)
    mcns_rois = mcns_rois[mcns_rois["FBbt_id"].notna() & (mcns_rois["FBbt_id"] != "")]
    # Nerves and the cervical connective are fibre tracts, not synaptic
    # neuropils, so they are not used as input/output regions.
    mcns_rois = mcns_rois[~mcns_rois["FBbt_name"].str.contains(TRACT_RE, regex=True)]
    raw_ROI_dict = dict(zip(mcns_rois["male-cns_region"], mcns_rois["FBbt_id"]))
    mcns_rois_FBbt = mcns_rois[["FBbt_id", "FBbt_name"]].drop_duplicates()
    ROI_name_dict = dict(zip(mcns_rois_FBbt["FBbt_id"], mcns_rois_FBbt["FBbt_name"]))

    fbbt = get_adapter(db_path)
    FBbt_descendants = {i: [x[0] for x in fbbt.relationships(objects=[i], predicates=["BFO:0000050"], include_entailed=True)]
                        for i in ROI_name_dict.keys()}
    # Add the neuPrint ROI hierarchy: part-of links that FBbt states only in
    # equivalence axioms (e.g. adult T1 leg neuropil) are not entailed in
    # fbbt-merged.db, which left the whole VNC listed next to its neuropils.
    with open(_proj("EM_neuropils", "male-cns_roi_hierarchy.json")) as f:
        for parent, parts in em.roi_hierarchy_parts(json.load(f), raw_ROI_dict).items():
            FBbt_descendants[parent] = list(set(FBbt_descendants.get(parent, [])) | parts)

    # hemilineage (from cache, replacing the live neuPrint query)
    hemilineages = pd.read_csv(_cache("male_cns_hemilineage.tsv"), sep="\t")
    mapped_hemilineages = hemilineages.merge(hemilineage_map, how="left", left_on="hemilineage", right_on="ito_lee_hemilineage")
    mapped_hemilineages = mapped_hemilineages[["mcns_type", "NB_id", "hemilineage"]].set_index("mcns_type").rename(columns={"NB_id": "neuroblast"})
    mapped_hemilineages = mapped_hemilineages[mapped_hemilineages["hemilineage"] != "putative_primary"]
    # Drop hemilineages another connectome contradicts, and any type whose
    # grouped members disagree (more than one hemilineage).
    excluded_hl = set(cell_types.index[cell_types["exclude_hemilineage"].astype(str).str.upper().eq("TRUE")])
    hl_counts = mapped_hemilineages.groupby(level=0)["hemilineage"].nunique()
    excluded_hl |= set(hl_counts.index[hl_counts > 1])
    mapped_hemilineages = mapped_hemilineages[~mapped_hemilineages.index.isin(excluded_hl)]
    mapped_hemilineages = mapped_hemilineages[~mapped_hemilineages.index.duplicated()]
    cell_types = cell_types.merge(mapped_hemilineages["neuroblast"], how="left", left_index=True, right_index=True)

    # connectivity (from cache) with the class-level consistency filter
    roiinfo = pd.read_csv(_cache("male_cns_roiinfo.tsv"), sep="\t")
    type_connectivity_table = em.laterality_connectivity(roiinfo, raw_ROI_dict)
    # Zero out regions another connectome contradicts (exclude_inputs /
    # exclude_outputs: '|'-separated FBbt ids), so they are neither asserted
    # nor written into the definition.
    tct = type_connectivity_table.reset_index()
    for col, polarity in (("exclude_inputs", "post"), ("exclude_outputs", "pre")):
        excluded = {(t, roi) for t, v in cell_types[col].items() for roi in _split(v)}
        if excluded:
            mask = [(t, roi) in excluded for t, roi in zip(tct["type"], tct["ROI"])]
            tct.loc[mask, polarity] = 0
    tct = tct[~(tct["post"].eq(0) & tct["pre"].eq(0))]
    type_connectivity_table = tct.set_index(["type", "laterality", "ROI"])

    def drop_redundant_terms(term_list):
        return em.drop_redundant_part_of(term_list, FBbt_descendants)

    def prune_nolat_against_lateralized(group):
        g = group.droplevel("type")
        if "no_laterality" not in g.index:
            return group
        ipsi = set(g["ipsilateral"]) if "ipsilateral" in g.index else set()
        contra = set(g["contralateral"]) if "contralateral" in g.index else set()
        lateralized = ipsi | contra
        if not lateralized:
            return group
        pruned = [i for i in g["no_laterality"] if not (set(FBbt_descendants.get(i, [])) & lateralized)]
        type_name = group.index.get_level_values("type")[0]
        group.loc[(type_name, "no_laterality")] = pruned
        return group

    connectivity_inputs = type_connectivity_table.loc[type_connectivity_table.loc[:, "post"] > CONNECTIVITY_THRESHOLD, "post"]
    connectivity_inputs = connectivity_inputs.reset_index("ROI").drop(columns=["post"])
    connectivity_inputs_lat = connectivity_inputs.groupby(["type", "laterality"])["ROI"].apply(list)
    connectivity_inputs_lat = connectivity_inputs_lat.apply(drop_redundant_terms)
    connectivity_inputs_lat = connectivity_inputs_lat.groupby(level="type", group_keys=False).apply(prune_nolat_against_lateralized)
    connectivity_inputs_nolat = connectivity_inputs.groupby("type")["ROI"].apply(list)
    connectivity_inputs_nolat = connectivity_inputs_nolat.apply(drop_redundant_terms)

    connectivity_outputs = type_connectivity_table.loc[type_connectivity_table.loc[:, "pre"] > CONNECTIVITY_THRESHOLD, "pre"]
    connectivity_outputs = connectivity_outputs.reset_index("ROI").drop(columns=["pre"])
    connectivity_outputs_lat = connectivity_outputs.groupby(["type", "laterality"])["ROI"].apply(list)
    connectivity_outputs_lat = connectivity_outputs_lat.apply(drop_redundant_terms)
    connectivity_outputs_lat = connectivity_outputs_lat.groupby(level="type", group_keys=False).apply(prune_nolat_against_lateralized)
    connectivity_outputs_nolat = connectivity_outputs.groupby("type")["ROI"].apply(list)
    connectivity_outputs_nolat = connectivity_outputs_nolat.apply(drop_redundant_terms)

    connectivity_regions_lat = connectivity_inputs_lat.to_frame(name="inputs").merge(
        connectivity_outputs_lat.to_frame(name="outputs"), how="outer", left_index=True, right_index=True)
    laterality = connectivity_regions_lat.reset_index("laterality").drop(labels=["inputs", "outputs"], axis=1)
    laterality = laterality.groupby("type")["laterality"].apply(list)

    def get_region_ids(mcns_type, lat, polarity):
        try:
            regions = connectivity_regions_lat.loc[(mcns_type, lat), polarity]
            return regions if isinstance(regions, list) else False
        except KeyError:
            return False

    def neuropil_writer(FBbt_ids):
        return em.name_lister([ROI_name_dict[i].replace("adult ", "") for i in FBbt_ids])

    def get_name_trunk(mcns_type):
        return re.match("[A-z]+", mcns_type)[0]

    def label_style(mcns_type):
        style = parent_types.loc[get_name_trunk(mcns_type), "label_style"]
        return style if isinstance(style, str) else "type"

    def label_writer(mcns_type):
        # label_style (broad_type_map): 'type' (default) -> adult <text> neuron <type>;
        # 'number' -> adult <text> neuron <digits> (as hemibrain/FlyWire AVLP001);
        # 'symbol' -> adult <type> neuron (as FlyWire CB0004, MANC AN07B015).
        trunk = get_name_trunk(mcns_type)
        broad_type = parent_types.loc[trunk, "text"]
        style = label_style(mcns_type)
        if style == "symbol":
            return f"adult {mcns_type} neuron"
        suffix = mcns_type[len(trunk):] if style == "number" else mcns_type
        if "neuron" in broad_type:
            return f"adult {broad_type} {suffix}"
        return f"adult {broad_type} neuron {suffix}"

    def opening_writer(mcns_type):
        """Definition opening. 'number'/'symbol' prefixes name a region or
        nothing, not a class, so these open with the first parent's label."""
        broad_type = parent_types.loc[get_name_trunk(mcns_type), "text"]
        if label_style(mcns_type) != "type":
            parent = _split(cell_types.loc[mcns_type, "additional_parents"])[0]
            name = fbbt.label(parent)
            return f"{name[0].upper()}{name[1:]} of the {mcns_type} group (Berg et al., 2026)."
        if "neuron" in broad_type:
            return f"Adult {broad_type} of the {mcns_type} group (Berg et al., 2026)."
        return f"Adult {broad_type} neuron of the {mcns_type} group (Berg et al., 2026)."

    def def_writer(mcns_type):
        ipsi_post = get_region_ids(mcns_type, "ipsilateral", "inputs")
        contra_post = get_region_ids(mcns_type, "contralateral", "inputs")
        nolat_post = get_region_ids(mcns_type, "no_laterality", "inputs")
        ipsi_pre = get_region_ids(mcns_type, "ipsilateral", "outputs")
        contra_pre = get_region_ids(mcns_type, "contralateral", "outputs")
        nolat_pre = get_region_ids(mcns_type, "no_laterality", "outputs")

        if any([ipsi_post, contra_post, nolat_post]):
            input_regions = []
            if ipsi_post:
                input_regions.append(f" the ipsilateral {neuropil_writer(ipsi_post)}")
            if contra_post:
                input_regions.append(f" the contralateral {neuropil_writer(contra_post)}")
            if nolat_post:
                input_regions.append(f" the {neuropil_writer(nolat_post)}")
            if len(input_regions) < 3:
                input_def = f" It receives input in{', and'.join(input_regions)} (Berg et al., 2026)."
            else:
                input_def = f" It receives input in{input_regions[0]},{input_regions[1]}, and{input_regions[2]} (Berg et al., 2026)."
        else:
            input_def = ""

        if any([ipsi_pre, contra_pre, nolat_pre]):
            output_regions = []
            if ipsi_pre:
                output_regions.append(f" the ipsilateral {neuropil_writer(ipsi_pre)}")
            if contra_pre:
                output_regions.append(f" the contralateral {neuropil_writer(contra_pre)}")
            if nolat_pre:
                output_regions.append(f" the {neuropil_writer(nolat_pre)}")
            if len(output_regions) < 3:
                output_def = f" It sends output to{', and'.join(output_regions)} (Berg et al., 2026)."
            else:
                output_def = f" It sends output to{output_regions[0]},{output_regions[1]}, and{output_regions[2]} (Berg et al., 2026)."
        else:
            output_def = ""

        try:
            hemilineage = (f" It belongs to the {mapped_hemilineages.loc[mcns_type, 'hemilineage'].replace('_',' ')}"
                           f" hemilineage (Berg et al., 2026).")
        except KeyError:
            hemilineage = ""

        definition = opening_writer(mcns_type)
        definition += hemilineage + input_def + output_def
        if cell_types["transmitter_pred"].notna().loc[mcns_type]:
            definition += (f" Its predicted neurotransmitter is {cell_types.loc[mcns_type, 'transmitter_pred']} "
                           "(Eckstein et al., 2024; Berg et al., 2026).")
        return definition

    def comment_writer(mcns_type):
        citations = []
        if cell_types["hemibrain_type"].notnull()[mcns_type]:
            citations.append("Scheffer et al., 2020")
        if cell_types["flywire_type"].notnull()[mcns_type]:
            citations.extend(["Schlegel et al., 2024", "Dorkenwald et al., 2024"])
        if cell_types["manc_type"].notnull()[mcns_type]:
            citations.append("Marin et al., 2024")
        citations.append("Berg et al., 2026")
        if cell_types["banc_type"].notnull()[mcns_type]:
            citations.append("Bates et al., 2026")
        citation_str = "; ".join(citations)
        if len(citations) == 1:
            comment = f"Cell type identified in one EM dataset ({citation_str})."
        else:
            comment = f"Cell type identified in multiple EM datasets ({citation_str})."
        comment += (f" Synapse locations are given where each cell of this type in "
                    f"neuprint has at least {CONNECTIVITY_THRESHOLD} connections.")
        if mcns_type in mapped_hemilineages.index:
            comment += " Hemilineage information from neuprint, though original source not clear."
        if pd.notna(cell_types.loc[mcns_type, "cross_check_comment"]):
            comment += " " + cell_types.loc[mcns_type, "cross_check_comment"]
        return comment

    def xref_generator(mcns_type):
        def_xrefs = ["doi:10.1016/j.cell.2026.08.015"]
        if cell_types["transmitter_pred"].notnull()[mcns_type]:
            def_xrefs.append("FlyBase:FBrf0259490")
        if cell_types["flywire_type"].notnull()[mcns_type]:
            def_xrefs.extend(["FlyBase:FBrf0260535", "FlyBase:FBrf0260546"])
        if cell_types["hemibrain_type"].notnull()[mcns_type]:
            def_xrefs.append("FlyBase:FBrf0246888")
        if cell_types["manc_type"].notnull()[mcns_type]:
            def_xrefs.append("doi:10.7554/eLife.97766.1")
        if cell_types["banc_type"].notnull()[mcns_type]:
            def_xrefs.append("doi:10.1038/s41586-026-10735-w")
        return "|".join(def_xrefs)

    cell_types["obo_id"] = cell_types["FBbt_id"]
    cell_types["obo_namespace"] = "fly_anatomy.ontology"
    cell_types["created_by"] = "http://orcid.org/0000-0002-1373-1705"
    cell_types["label"] = cell_types.index.to_series().apply(label_writer)
    cell_types["definition"] = cell_types.index.to_series().apply(def_writer)
    cell_types["Xref_def"] = cell_types.index.to_series().apply(xref_generator)
    cell_types["comment"] = cell_types.index.to_series().apply(comment_writer)
    cell_types["NT"] = cell_types["transmitter_pred"].map(NT_CVS)

    cell_types["broad_type"] = cell_types.index.to_series().apply(get_name_trunk)
    cell_types = cell_types.reset_index(drop=False)
    cell_types = cell_types.merge(parent_types["FBbt_id"].reset_index().rename(columns={"FBbt_id": "type_parent"}),
                                  how="left", on="broad_type")
    cell_types = cell_types.set_index("mcns_type")
    cell_types["parents"] = cell_types.apply(
        lambda row: "|".join(p for p in (row["additional_parents"], row["type_parent"]) if pd.notna(p) and p), axis=1)

    cell_types["inputs"] = connectivity_inputs_nolat.apply(lambda x: "|".join(x))
    cell_types["outputs"] = connectivity_outputs_nolat.apply(lambda x: "|".join(x))
    cell_types["laterality"] = laterality.apply(lambda x: "PATO:0000618" if "contralateral" in x else "")

    for col in ["hemibrain_type", "flywire_type", "manc_type"]:
        cell_types[col] = cell_types[col].apply(lambda x: {"X": np.nan}.get(x, x))
        # A name identical to the male-CNS type is already the term's symbol
        # (exact synonym), so it is not repeated as a related synonym.
        cell_types[col] = [("|".join(n for n in _split(v) if n != t) or np.nan)
                           for t, v in zip(cell_types.index, cell_types[col])]
    cell_types.loc[cell_types["hemibrain_type"].notnull(), "hemibrain_ref"] = "FlyBase:FBrf0246888|doi:10.1016/j.cell.2026.08.015"
    cell_types.loc[cell_types["flywire_type"].notnull(), "flywire_ref"] = "FlyBase:FBrf0260535|doi:10.1016/j.cell.2026.08.015"
    cell_types.loc[cell_types["manc_type"].notnull(), "manc_ref"] = "doi:10.7554/eLife.97766.1|doi:10.1016/j.cell.2026.08.015"

    template = pd.DataFrame.from_records([TEMPLATE_SEED])
    cell_types = cell_types.rename(columns={"FBbt_id": "ID"})
    cell_types = cell_types.drop(["transmitter_pred", "additional_parents", "broad_type", "type_parent"]
                                 + OPTIONAL_COLUMNS, axis=1)
    populated_template = pd.concat([template, cell_types])
    return populated_template


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="template.tsv")
    ap.add_argument("--db", default=_default_db(), help="path to fbbt-merged.db (OAK)")
    args = ap.parse_args()
    template = build_template(args.db)
    template.to_csv(args.out, sep="\t", index=False)
    print(f"Wrote {len(template)} rows -> {args.out}")


if __name__ == "__main__":
    main()
