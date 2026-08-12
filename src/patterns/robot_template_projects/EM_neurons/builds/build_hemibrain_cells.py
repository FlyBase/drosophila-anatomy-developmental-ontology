#!/usr/bin/env python3
"""Build the hemibrain provisional-cell-type ROBOT template (offline).

Faithful port of hemibrain_new_types/update_new_types.ipynb. Reads the committed
hemibrain evidence cache (hemibrain_roiinfo.tsv) instead of querying neuPrint
live, plus the curated new_cell_types.tsv + ROI mapping, and filters out types
already covered by FlyWire. No network/token.

Usage:
    python3 build_hemibrain_cells.py [--out template.tsv]
"""

import argparse
import os
import re
import sys
from collections import OrderedDict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import EM_common as em  # noqa: E402

CONNECTIVITY_THRESHOLD = 10

TI_PATTERN = re.compile("([A-Z]+)([0-9][0-9][0-9]$)")
MULTIPN_PATTERN = re.compile("(M_)([lvad]+[2]?)(PN)([0-9]*[mlt]+)([0-9]+[A-Z]?)")

NB_DATA = np.array([
    ["FBbt:00067348", "v", "ALv1"], ["FBbt:00050035", "v2", "ALv2"],
    ["FBbt:00050038", "lv", "ALlv1"], ["FBbt:00067346", "ad", "ALad1"],
    ["FBbt:00067347", "l", "ALl1 (Notch OFF hemilineage)"],
    ["FBbt:00067347", "l2", "ALl1 (Notch ON hemilineage)"],
])
NEUROBLASTS = pd.DataFrame(NB_DATA, columns=["ID", "short", "name"]).set_index("short")

TRACT_DATA = np.array([
    ["FBbt:00003985", "m", "medial antennal lobe tract"],
    ["FBbt:00003983", "l", "lateral antennal lobe tract"],
    ["FBbt:00003984", "ml", "mediolateral antennal lobe tract"],
    ["FBbt:00049719", "10t", "transverse antennal lobe t10ALT tract"],
])
TRACTS = pd.DataFrame(TRACT_DATA, columns=["ID", "short", "name"]).set_index("short")

TEMPLATE_SEED = OrderedDict([
    ("ID", "ID"), ("CLASS_TYPE", "CLASS_TYPE"), ("TYPE", "TYPE"),
    ("obo_id", "A oboInOwl:id"), ("obo_namespace", "A oboInOwl:hasOBONamespace"),
    ("label", "A rdfs:label"), ("definition", "A IAO:0000115"),
    ("Xref_def", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("created_by", "AI dc:contributor"), ("creation_date", "AT dc:date^^xsd:dateTime"),
    ("synonym", "A oboInOwl:hasExactSynonym"), ("syn_ref", ">A oboInOwl:hasDbXref"),
    ("additional_synonym", "A oboInOwl:hasRelatedSynonym"),
    ("additional_synonym_ref", ">A oboInOwl:hasDbXref"), ("comment", "A rdfs:comment"),
    ("synapses", "SC 'has synaptic IO in region' some %"),
    ("inputs", "SC 'receives synaptic input in region' some % SPLIT=|"),
    ("parent", "SC % SPLIT=|"), ("neuroblast", "SC 'develops from' some %"),
    ("tract", "SC 'fasciculates with' some %"), ("hemilineage", "SC %"),
    ("outputs", "SC 'sends synaptic output to region' some % SPLIT=|"),
])


def _src(project, *parts):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", project, *parts))


def _cache(name):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "data", name))


def build_template():
    cell_types = pd.read_csv(_src("hemibrain_new_types", "new_cell_types.tsv"),
                             sep="\t", dtype="str", na_filter=False)

    # Filter out types already covered by FlyWire annotations.
    flywire_annotations = pd.read_csv(
        _src("flywire_neurons", "Supplemental_file1_neuron_annotations.tsv"),
        sep="\t", dtype="str",
    )
    cell_types = cell_types[~(
        cell_types["np_type"].isin(flywire_annotations["cell_type"])
        | cell_types["np_type"].isin(flywire_annotations["hemibrain_type"])
    )].reset_index()

    # ROI mapping (+ extra regions), raw dict built BEFORE stripping L/R.
    full_roi_mapping = pd.read_csv(_src("hemibrain_new_types", "hemibrain_1-1_ROI_mapping.tsv"), sep="\t")
    extra_regions = pd.DataFrame({
        "ROI": ["PS(R)", "PS(L)", "CL(R)", "CL(L)"],
        "FBbt_id": ["FBbt:00040072", "FBbt:00040072", "FBbt:00040047", "FBbt:00040047"],
        "FBbt_name": ["posterior slope", "posterior slope", "clamp", "clamp"],
    })
    full_roi_mapping = pd.concat([full_roi_mapping, extra_regions], ignore_index=True)
    full_roi_mapping["ROI"] = full_roi_mapping["ROI"].apply(lambda x: x.strip("'"))

    raw_ROI_dict = dict(zip(full_roi_mapping["ROI"], full_roi_mapping["FBbt_id"]))

    tidy_roi_mapping = full_roi_mapping.copy()
    tidy_roi_mapping["ROI"] = tidy_roi_mapping["ROI"].map(lambda x: re.compile(r"\([LR]+\)").sub("", x))
    tidy_roi_mapping = tidy_roi_mapping[tidy_roi_mapping["ROI"].str.match("[A-Z]+$") == True]  # noqa: E712
    tidy_roi_mapping = tidy_roi_mapping.drop_duplicates().reset_index(drop=True)

    # Connectivity from the committed cache (replaces the live neuPrint query).
    #
    # The notebook does ROIs.apply(pd.Series).stack(future_stack=True) then
    # .apply(pd.Series).fillna(0), which materialises a ZERO for every
    # (body, region) pair a body lacks. The subsequent groupby(type,ROI).min()
    # is therefore 0 for any region not present in EVERY body of the type -->
    # those are dropped. This is a class-level consistency filter that keeps only
    # regions shared by all individuals of a type. Our cache stores only present
    # (body, region) pairs, so we reconstruct the "present in all bodies"
    # requirement here: a region survives only if the number of bodies carrying
    # it equals the type's total body count.
    cache = pd.read_csv(_cache("hemibrain_roiinfo.tsv"), sep="\t")
    nbodies = cache.groupby("type")["bodyId"].nunique()  # all bodies per type
    mapped = cache.assign(ROI=cache["roi"].map(raw_ROI_dict)).dropna(subset=["ROI"])
    body_ct = mapped.groupby(["type", "bodyId", "ROI"], as_index=False).agg(post=("post", "max"), pre=("pre", "max"))
    agg = body_ct.groupby(["type", "ROI"]).agg(
        post=("post", "min"), pre=("pre", "min"), n=("bodyId", "nunique")).reset_index()
    agg = agg.merge(nbodies.rename("nbodies"), left_on="type", right_index=True)
    # regions absent from any body of the type -> treated as 0 (min over zeros)
    agg.loc[agg["n"] < agg["nbodies"], ["post", "pre"]] = 0
    agg = agg[~(agg["post"].eq(0) & agg["pre"].eq(0))]
    agg = agg.sort_values(["type", "ROI"]).reset_index(drop=True)
    type_connectivity_table = agg.set_index(["type", "ROI"])[["post", "pre"]]

    def type_checker(shortname):
        if re.match(TI_PATTERN, shortname):
            return "TI"
        elif re.match(MULTIPN_PATTERN, shortname):
            return "multi"
        raise ValueError("Invalid neuron name - " + shortname)

    def shortname_splitter(shortname):
        name_type = type_checker(shortname)
        m = re.match(TI_PATTERN if name_type == "TI" else MULTIPN_PATTERN, shortname)
        if m:
            return m.groups()
        raise ValueError(shortname + "could not be split.")

    def neuropil_writer(roi):
        if re.match("FBbt", roi):
            neuropil = str(list(full_roi_mapping[full_roi_mapping["FBbt_id"] == roi]["FBbt_name"])[0])
        elif roi in list(tidy_roi_mapping["ROI"]):
            neuropil = str(list(tidy_roi_mapping[tidy_roi_mapping["ROI"] == roi]["FBbt_name"])[0])
        elif roi in list(full_roi_mapping["ROI"]):
            neuropil = str(list(full_roi_mapping[full_roi_mapping["ROI"] == roi]["FBbt_name"])[0])
        else:
            raise KeyError("Input to neuropil_writer must be a valid roi or FBbt ID!")
        return neuropil.replace("adult ", "")

    def label_maker(shortname):
        if type_checker(shortname) == "TI":
            neuropil = neuropil_writer(shortname_splitter(shortname)[0])
            return "adult %s neuron %s" % (neuropil, shortname_splitter(shortname)[1])
        elif type_checker(shortname) == "multi":
            return "adult multiglomerular antennal lobe projection neuron type %s %sPN" % (
                shortname_splitter(shortname)[4], shortname_splitter(shortname)[1])
        raise ValueError("Could not make label for " + shortname)

    def definition_maker(shortname):
        definition = ""
        if type_checker(shortname) == "TI":
            definition += ("Adult neuron belonging to group %s of the terra incognita neurons "
                           "with substantial synapsing in the %s (Scheffer et al., 2020)."
                           % (shortname_splitter(shortname)[1], neuropil_writer(shortname_splitter(shortname)[0])))
        elif type_checker(shortname) == "multi":
            definition += ("Adult multiglomerular antennal lobe projection neuron belonging to group %s "
                           "(Scheffer et al., 2020). It develops from neuroblast %s and follows "
                           "the %s (Bates et al., 2020; Scheffer et al., 2020)."
                           % (shortname_splitter(shortname)[4], NEUROBLASTS["name"][shortname_splitter(shortname)[1]],
                              TRACTS["name"][shortname_splitter(shortname)[3]]))
        else:
            raise ValueError("Could not make definition for " + shortname)

        try:
            type_connectivity = type_connectivity_table.loc[shortname]
            postsynapses = [r for r in type_connectivity.index
                            if type_connectivity["post"][r] >= CONNECTIVITY_THRESHOLD]
            if postsynapses:
                names = [neuropil_writer(i) for i in postsynapses]
                definition += " It has postsynaptic sites in the %s (Scheffer et al., 2020)." % em.name_lister(names)
            presynapses = [r for r in type_connectivity.index
                           if type_connectivity["pre"][r] >= CONNECTIVITY_THRESHOLD]
            if presynapses:
                names = [neuropil_writer(i) for i in presynapses]
                definition += " It has presynaptic sites in the %s (Scheffer et al., 2020)." % em.name_lister(names)
        except KeyError:
            pass
        return definition

    template = pd.DataFrame.from_records([TEMPLATE_SEED])

    for i in cell_types.index:
        row_od = OrderedDict((c, "") for c in template.columns)
        np_type = cell_types["np_type"][i]

        Parents_list = []
        if cell_types.asserted_parents[i]:
            Parents_list.extend(cell_types.asserted_parents[i].split("|"))

        row_od["CLASS_TYPE"] = "subclass"
        row_od["TYPE"] = "owl:Class"
        row_od["created_by"] = "http://orcid.org/0000-0002-1373-1705"
        row_od["creation_date"] = cell_types["date"][i]
        row_od["comment"] = ("Uncharacterized putative cell type (based on clustering analysis) "
                             "from Janelia hemibrain data (Scheffer et al., 2020).")
        row_od["obo_namespace"] = "fly_anatomy.ontology"
        row_od["ID"] = cell_types["FBbt_id"][i]
        row_od["obo_id"] = cell_types["FBbt_id"][i]
        row_od["synonym"] = "adult %s neuron" % np_type
        row_od["syn_ref"] = cell_types["ref"][i]
        row_od["additional_synonym"] = cell_types["synonym"][i]
        row_od["additional_synonym_ref"] = cell_types["synonym_ref"][i]
        row_od["label"] = label_maker(np_type)
        row_od["definition"] = definition_maker(np_type)
        row_od["Xref_def"] = cell_types["ref"][i]

        if type_checker(np_type) == "TI":
            Parents_list.append("FBbt:00047095")
            row_od["synapses"] = str(list(
                tidy_roi_mapping[tidy_roi_mapping["ROI"] == shortname_splitter(np_type)[0]]["FBbt_id"])[0])
        if type_checker(np_type) == "multi":
            Parents_list.append("FBbt:00007441")
            row_od["neuroblast"] = NEUROBLASTS["ID"][shortname_splitter(np_type)[1]]
            row_od["tract"] = TRACTS["ID"][shortname_splitter(np_type)[3]]
            row_od["inputs"] = str(list(tidy_roi_mapping[tidy_roi_mapping["ROI"] == "AL"]["FBbt_id"])[0])
            row_od["Xref_def"] += "|FlyBase:FBrf0246460"

        if "Notch OFF" in row_od["definition"]:
            row_od["hemilineage"] = "FBbt:00049540"
        elif "Notch ON" in row_od["definition"]:
            row_od["hemilineage"] = "FBbt:00049539"

        if np_type in type_connectivity_table.index:
            row_od["comment"] += (" Connectivity based on Hemibrain v1.2.1 data where each individual of this type "
                                  "has at least %s synapses in a region." % CONNECTIVITY_THRESHOLD)

        try:
            type_connectivity = type_connectivity_table.loc[np_type]
            postsynapses = [r for r in type_connectivity.index
                            if type_connectivity["post"][r] >= CONNECTIVITY_THRESHOLD]
            if postsynapses:
                row_od["inputs"] = "|".join(postsynapses)
            presynapses = [r for r in type_connectivity.index
                           if type_connectivity["pre"][r] >= CONNECTIVITY_THRESHOLD]
            if presynapses:
                row_od["outputs"] = "|".join(presynapses)
        except KeyError:
            pass

        row_od["parent"] = "|".join(Parents_list)
        template = pd.concat([template, pd.DataFrame.from_records([row_od])], ignore_index=True, sort=False)

    # ROBOT issue #1105 workaround.
    template = pd.concat([template, em.type_rows_for_referenced_curies(template)], ignore_index=True)
    return template


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="template.tsv")
    args = ap.parse_args()
    template = build_template()
    template.to_csv(args.out, sep="\t", header=True, index=False)
    print(f"Wrote {len(template)} rows -> {args.out}")


if __name__ == "__main__":
    main()
