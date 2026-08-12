#!/usr/bin/env python3
"""Build the optic-lobe neuron-term ROBOT template (offline).

Faithful port of optic_lobe/optic_lobe_neurons.ipynb. Reads committed data: the
optic-lobe evidence caches (optic_lobe_roiinfo.tsv, optic_lobe_hemilineage.tsv),
curated maps, and the FlyWire lineage map; uses OAK against tmp/fbbt-merged.db
for part-of pruning; reconstructs the class-level connectivity-consistency filter
via EM_common.laterality_connectivity. No network/token.

This generator does NOT use the ROBOT #1105 TYPE-row workaround (matching the
original); build with `robot template --input fbbt.owl`.

Usage:
    python3 build_optic_lobe.py [--out template.tsv] [--db .../fbbt-merged.db]
"""

import argparse
import os
import re
import sys
from collections import OrderedDict

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import EM_common as em  # noqa: E402

CONNECTIVITY_THRESHOLD = 10
NT_CVS = {"acetylcholine": "GO:0014055", "GABA": "GO:0061534", "glutamate": "GO:0061535"}
MATSLIAH_REVISED_OL_TYPES = {
    "Cm18", "Cm20", "Cm29", "Cm31a", "Cm31b", "Cm32", "Cm34", "Cm35",
    "Li31", "Li32", "Li33", "Li38", "Li39",
}


def _proj(*parts):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", *parts))


def _cache(name):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "data", name))


def _default_db():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "..", "..", "ontology", "tmp", "fbbt-merged.db"))


TEMPLATE_SEED = OrderedDict([
    ("ID", "ID"),
    ("obo_id", "A oboInOwl:id"), ("obo_namespace", "A oboInOwl:hasOBONamespace"),
    ("label", "A rdfs:label"), ("definition", "A IAO:0000115"),
    ("Xref_def", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("created_by", "AI dc:contributor"), ("creation_date", "AT dc:date^^xsd:dateTime"),
    ("Matsliah_type", "A oboInOwl:hasRelatedSynonym SPLIT=|"),
    ("Matsliah_ref", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("Schlegel_type", "A oboInOwl:hasRelatedSynonym SPLIT=|"),
    ("Schlegel_ref", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("hemibrain_type", "A oboInOwl:hasRelatedSynonym SPLIT=|"),
    ("hemibrain_ref", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("comment", "A rdfs:comment"),
    ("parents", "SC % SPLIT=|"),
    ("NT", "SC 'capable of' some %"),
    ("inputs", "SC 'receives synaptic input in region' some % SPLIT=|"),
    ("outputs", "SC 'sends synaptic output to region' some % SPLIT=|"),
    ("laterality", "SC 'has characteristic' some %"),
    ("neuroblast", "SC 'develops from' some %"),
])


def build_template(db_path):
    import numpy as np  # noqa: F401  (parity with notebook imports)
    from oaklib import get_adapter

    cell_types = pd.read_csv(_proj("optic_lobe", "new_types.tsv"), sep="\t", low_memory=False, index_col="OL_type")
    parent_types = pd.read_csv(_proj("optic_lobe", "broad_type_map.tsv"), sep="\t", low_memory=False, index_col="broad_type")
    hemilineage_map = pd.read_csv(_proj("flywire_neurons", "lineage_map.tsv"), sep="\t", low_memory=False)
    OL_rois = pd.read_csv(_proj("optic_lobe", "OL_ROI_mapping.tsv"), sep="\t")
    raw_ROI_dict = dict(zip(OL_rois["ROI"], OL_rois["FBbt_id"]))
    OL_rois_FBbt = OL_rois[["FBbt_id", "FBbt_name"]].drop_duplicates()
    ROI_name_dict = dict(zip(OL_rois_FBbt["FBbt_id"], OL_rois_FBbt["FBbt_name"]))

    fbbt = get_adapter(db_path)
    FBbt_descendants = {i: [x[0] for x in fbbt.relationships(objects=[i], predicates=["BFO:0000050"], include_entailed=True)]
                        for i in ROI_name_dict.keys()}

    hemilineages = pd.read_csv(_cache("optic_lobe_hemilineage.tsv"), sep="\t")
    mapped_hemilineages = hemilineages.merge(hemilineage_map, how="left", left_on="hemilineage", right_on="ito_lee_hemilineage")
    unmapped = [i for i in hemilineages["hemilineage"].to_list() if i not in mapped_hemilineages["hemilineage"].to_list()]
    mapped_hemilineages = mapped_hemilineages[["OL_type", "NB_id", "hemilineage"]].set_index("OL_type").rename(columns={"NB_id": "neuroblast"})
    mapped_hemilineages = mapped_hemilineages[mapped_hemilineages["hemilineage"] != "putative_primary"]
    cell_types = cell_types.merge(mapped_hemilineages["neuroblast"], how="left", left_index=True, right_index=True)

    roiinfo = pd.read_csv(_cache("optic_lobe_roiinfo.tsv"), sep="\t")
    type_connectivity_table = em.laterality_connectivity(roiinfo, raw_ROI_dict)

    def drop_redundant_terms(term_list):
        return em.drop_redundant_part_of(term_list, FBbt_descendants)

    connectivity_inputs = type_connectivity_table.loc[type_connectivity_table.loc[:, "post"] > CONNECTIVITY_THRESHOLD, "post"]
    connectivity_inputs = connectivity_inputs.reset_index("ROI").drop(columns=["post"], axis=1)
    connectivity_inputs_lat = connectivity_inputs.groupby(["type", "laterality"])["ROI"].apply(list).apply(drop_redundant_terms)
    connectivity_inputs_nolat = connectivity_inputs.groupby("type")["ROI"].apply(list).apply(drop_redundant_terms)

    connectivity_outputs = type_connectivity_table.loc[type_connectivity_table.loc[:, "pre"] > CONNECTIVITY_THRESHOLD, "pre"]
    connectivity_outputs = connectivity_outputs.reset_index("ROI").drop(columns=["pre"], axis=1)
    connectivity_outputs_lat = connectivity_outputs.groupby(["type", "laterality"])["ROI"].apply(list).apply(drop_redundant_terms)
    connectivity_outputs_nolat = connectivity_outputs.groupby("type")["ROI"].apply(list).apply(drop_redundant_terms)

    connectivity_regions_lat = connectivity_inputs_lat.to_frame(name="inputs").merge(
        connectivity_outputs_lat.to_frame(name="outputs"), how="outer", left_index=True, right_index=True)
    laterality = connectivity_regions_lat.reset_index("laterality").drop(labels=["inputs", "outputs"], axis=1)
    laterality = laterality.groupby("type")["laterality"].apply(list)

    def get_region_ids(OL_type, lat, polarity):
        try:
            regions = connectivity_regions_lat.loc[(OL_type, lat), polarity]
            return regions if isinstance(regions, list) else False
        except KeyError:
            return False

    def neuropil_writer(FBbt_ids):
        return em.name_lister([ROI_name_dict[i].replace("adult ", "") for i in FBbt_ids])

    def get_name_trunk(OL_type):
        return re.match("[A-z]+", OL_type)[0]

    def label_writer(OL_type):
        broad_type = parent_types.loc[get_name_trunk(OL_type), "text"]
        if "neuron" in broad_type:
            return f"adult {broad_type} {OL_type}"
        return f"adult {broad_type} neuron {OL_type}"

    def def_writer(OL_type):
        broad_type = parent_types.loc[get_name_trunk(OL_type), "text"]
        ipsi_post = get_region_ids(OL_type, "ipsilateral", "inputs")
        contra_post = get_region_ids(OL_type, "contralateral", "inputs")
        nolat_post = get_region_ids(OL_type, "no_laterality", "inputs")
        ipsi_pre = get_region_ids(OL_type, "ipsilateral", "outputs")
        contra_pre = get_region_ids(OL_type, "contralateral", "outputs")
        nolat_pre = get_region_ids(OL_type, "no_laterality", "outputs")

        if any([ipsi_post, contra_post, nolat_post]):
            input_regions = []
            if ipsi_post:
                input_regions.append(f" the ipsilateral {neuropil_writer(ipsi_post)}")
            if contra_post:
                input_regions.append(f" the contralateral {neuropil_writer(contra_post)}")
            if nolat_post:
                input_regions.append(f" the {neuropil_writer(nolat_post)}")
            if len(input_regions) < 3:
                input_def = f" It receives input in{', and'.join(input_regions)} (Nern et al., 2025)."
            else:
                input_def = f" It receives input in{input_regions[0]},{input_regions[1]}, and{input_regions[2]} (Nern et al., 2025)."
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
                output_def = f" It sends output to{', and'.join(output_regions)} (Nern et al., 2025)."
            else:
                output_def = f" It sends output to{output_regions[0]},{output_regions[1]}, and{output_regions[2]} (Nern et al., 2025)."
        else:
            output_def = ""

        try:
            hemilineage = (f" It belongs to the {mapped_hemilineages.loc[OL_type, 'hemilineage'].replace('_',' ')}"
                           f" hemilineage (Nern et al., 2025).")
        except KeyError:
            hemilineage = ""

        if cell_types.loc[OL_type, "matched_as"] == "1-to-1":
            av_cells = cell_types.loc[OL_type, ["OL", "Matsliah"]].mean()
        else:
            av_cells = cell_types.loc[OL_type, "OL"]

        if "neuron" in broad_type:
            definition = f"Adult {broad_type} of the {OL_type} group (Nern et al., 2025)."
        else:
            definition = f"Adult {broad_type} neuron of the {OL_type} group (Nern et al., 2025)."
        definition += hemilineage + input_def + output_def
        if cell_types["transmitter_pred"].notna().loc[OL_type]:
            definition += (f" Its predicted neurotransmitter is {cell_types.loc[OL_type, 'transmitter_pred']} "
                           "(Eckstein et al., 2024; Nern et al., 2025).")
        if int(round(av_cells, 0)) == 1:
            definition += " There is one of these cells per hemisphere (Nern et al., 2025)."
        else:
            definition += f" There are approximately {int(round(av_cells, 0))} of these cells per hemisphere (Nern et al., 2025)."
        if cell_types.loc[OL_type, "jigsaw"] == "y":
            definition += " The pair of them form a jigsaw pattern, tiling the neuropil (Matsliah et al., 2024)."
        return definition

    def comment_writer(OL_type):
        light = " and at light level" if cell_types.loc[OL_type, "LM"] == "y" else ""
        citations = []
        if cell_types["hemibrain_type"].notnull()[OL_type]:
            citations.append("Scheffer et al., 2020")
        if cell_types["Schlegel_type"].notnull()[OL_type] or cell_types["Matsliah_type"].notnull()[OL_type]:
            citations.extend(["Schlegel et al., 2024", "Dorkenwald et al., 2024"])
        if cell_types["Matsliah_type"].notnull()[OL_type]:
            citations.append("Matsliah et al., 2024")
        citations.append("Nern et al., 2025")
        citation_str = "; ".join(citations)
        if cell_types.loc[OL_type, "matched_as"] == "unmatched":
            comment = f"Cell type identified in one EM dataset{light} (Nern et al., 2025)."
        else:
            comment = f"Cell type identified in multiple EM datasets{light} ({citation_str})."
        comment += (f" Synapse locations are given where each cell of this type in "
                    f"neuprint has at least {CONNECTIVITY_THRESHOLD} connections.")
        if OL_type in mapped_hemilineages.index:
            comment += " Hemilineage information from neuprint, though original source not clear."
        if OL_type == "LoVP26":
            comment += (" This cell type was originally hemibrain PS179 (Scheffer et al., 2020 - FBrf0246888)."
                        " Modification to LoVP26 is a slight broadening of meaning.")
        if OL_type in MATSLIAH_REVISED_OL_TYPES:
            comment += (" The Matsliah mapping for this cell type is different to that in "
                        "Nern et al. (2025) and is based on an unpublished updated version "
                        "of the cell type mapping table.")
        comment += " Other information from Nern et al. (2025) supplements."
        return comment

    def xref_generator(OL_type):
        def_xrefs = ["FlyBase:FBrf0262545"]
        if cell_types["transmitter_pred"].notnull()[OL_type]:
            def_xrefs.append("FlyBase:FBrf0259490")
        if cell_types["Matsliah_type"].notnull()[OL_type]:
            def_xrefs.extend(["FlyBase:FBrf0260535", "FlyBase:FBrf0260546", "FlyBase:FBrf0260545"])
        elif cell_types["Schlegel_type"].notnull()[OL_type]:
            def_xrefs.extend(["FlyBase:FBrf0260535", "FlyBase:FBrf0260546"])
        if cell_types["hemibrain_type"].notnull()[OL_type]:
            def_xrefs.append("FlyBase:FBrf0246888")
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
    cell_types = cell_types.set_index("OL_type")
    cell_types["parents"] = cell_types.apply(
        lambda row: f"{row['additional_parents']}|{row['type_parent']}" if pd.notna(row["additional_parents"]) else row["type_parent"], axis=1)

    cell_types["inputs"] = connectivity_inputs_nolat.apply(lambda x: "|".join(x))
    cell_types["outputs"] = connectivity_outputs_nolat.apply(lambda x: "|".join(x))
    cell_types["laterality"] = laterality.apply(lambda x: "PATO:0000618" if "contralateral" in x else "")

    for col in ["Matsliah_type", "Schlegel_type", "hemibrain_type"]:
        cell_types[col] = cell_types[col].apply(lambda x: {"X": float("nan")}.get(x, x))
    cell_types.loc[cell_types["Matsliah_type"].notnull(), "Matsliah_ref"] = "FlyBase:FBrf0260545|FlyBase:FBrf0262545"
    cell_types.loc[cell_types["Schlegel_type"].notnull(), "Schlegel_ref"] = "FlyBase:FBrf0260535|FlyBase:FBrf0262545"
    cell_types.loc[cell_types["hemibrain_type"].notnull(), "hemibrain_ref"] = "FlyBase:FBrf0246888|FlyBase:FBrf0262545"

    template = pd.DataFrame.from_records([TEMPLATE_SEED])
    cell_types = cell_types.rename(columns={"FBbt_id": "ID"})
    cell_types = cell_types.drop(["OL", "Matsliah", "transmitter_pred", "matched_as", "additional_parents",
                                  "jigsaw", "LM", "broad_type", "type_parent"], axis=1)
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
