#!/usr/bin/env python3
"""Build the hemibrain antennal-lobe local-neuron (ALLN) ROBOT template.

Faithful port of hemibrain_new_types/ALLNs.ipynb. Pure build from committed
TSVs (new_ALLNs.tsv, glomerulus_names.tsv); no neuPrint fetch. NOTE: this
generator does NOT use the ROBOT #1105 TYPE-row workaround (matching the
original), and uses 'A dc:contributor' (not 'AI').

Usage:
    python3 build_hemibrain_allns.py [--out template.tsv]
"""

import argparse
import os
import re
from collections import OrderedDict

import numpy as np
import pandas as pd

LN_PATTERN = re.compile("([lv]+[2]?)(LN)([0-9]+[A-Z]?)")

NB_DATA = np.array([
    ["FBbt:00067348", "v", "ALv1"], ["FBbt:00050035", "v2", "ALv2"],
    ["FBbt:00050038", "lv", "ALlv1"], ["FBbt:00067346", "ad", "ALad1"],
    ["FBbt:00067347", "l", "ALl1 (Notch OFF hemilineage)"],
    ["FBbt:00067347", "l2", "ALl1 (Notch ON hemilineage)"],
])
NEUROBLASTS = pd.DataFrame(NB_DATA, columns=["ID", "short", "name"]).set_index("short")

PATTERNS_DICT = {"broad": "FBbt:00051500", "regional": "FBbt:00049644",
                 "sparse": "FBbt:00049647", "patchy": "FBbt:00049646"}

TEMPLATE_SEED = OrderedDict([
    ("ID", "ID"), ("CLASS_TYPE", "CLASS_TYPE"), ("RDF_Type", "TYPE"),
    ("obo_id", "A oboInOwl:id"), ("obo_namespace", "A oboInOwl:hasOBONamespace"),
    ("label", "A rdfs:label"), ("definition", "A IAO:0000115"),
    ("Xref_def", ">A oboInOwl:hasDbXref SPLIT=|"),
    # NB: the original ALLNs.ipynb used 'A dc:contributor' (literal ORCID); the
    # released component and house style use an IRI value, so use 'AI'.
    ("created_by", "AI dc:contributor"), ("creation_date", "AT dc:date^^xsd:dateTime"),
    ("synonym", "A oboInOwl:hasExactSynonym"), ("comment", "A rdfs:comment"),
    ("glomeruli", "SC 'has synaptic IO in region' some % SPLIT=|"),
    ("inputs_AL", "SC 'receives synaptic input in region' some %"),
    ("outputs_AL", "SC 'sends synaptic output to region' some %"),
    ("parent", "SC %"), ("arbor_type", "SC %"),
    ("neuroblast", "SC 'develops from' some %"), ("hemilineage", "SC %"),
])


def _src(*parts):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "sources", "hemibrain", *parts))


def shortname_splitter(shortname):
    m = re.match(LN_PATTERN, shortname)
    if m:
        return m.groups()
    raise ValueError(shortname + "could not be split.")


def glomerulus_lister(glomeruli):
    if (len(glomeruli) == 1) and (glomeruli[0] == "VP"):
        return "the %s glomeruli" % glomeruli[0]
    if len(glomeruli) == 1:
        return "the %s glomerulus" % glomeruli[0]
    glom_str = "the "
    while len(glomeruli) > 1:
        glom_str += "%s, " % glomeruli[0]
        glomeruli = glomeruli[1:]
    glom_str = glom_str.rstrip(", ")
    glom_str += " and %s glomeruli" % glomeruli[0]
    return glom_str


def definition_maker(shortname, laterality, pattern, glomeruli):
    lineage = "neuroblast %s" % NEUROBLASTS["name"][shortname_splitter(shortname)[0]]
    group = shortname_splitter(shortname)[2]
    if laterality == "uni":
        lat = "It is unilateral"
    elif laterality == "bi":
        lat = "It is bilateral"
    pat = "and it has a %s arborization pattern" % pattern
    if glomeruli:
        glom = ", with strongest innervation in %s (Schlegel et al., 2021)." % glomerulus_lister(glomeruli)
    else:
        glom = " (Schlegel et al., 2021)."
    return str("Adult local neuron of the antennal lobe that develops from %s and belongs to group %s "
               "(Schlegel et al., 2021). %s %s%s" % (lineage, group, lat, pat, glom))


def build_template():
    cell_types = pd.read_csv(_src("new_ALLNs.tsv"), sep="\t")
    glomeruli = pd.read_csv(_src("glomerulus_names.tsv"), sep="\t", index_col="name")
    glomeruli_dict = glomeruli.to_dict(orient="dict")["FBbt_ID"]

    template = pd.DataFrame.from_records([TEMPLATE_SEED])

    for i in cell_types.index:
        row_od = OrderedDict((c, "") for c in template.columns)
        np_type = cell_types["np_type"][i]

        row_od["CLASS_TYPE"] = "subclass"
        row_od["RDF_Type"] = "owl:Class"
        row_od["created_by"] = "http://orcid.org/0000-0002-1373-1705"
        row_od["comment"] = "Cell type described based on Janelia hemibrain data (Schlegel et al., 2021)."
        row_od["parent"] = "FBbt:00007390"
        row_od["inputs_AL"] = "FBbt:00007401"
        row_od["outputs_AL"] = "FBbt:00007401"
        row_od["obo_namespace"] = "fly_anatomy.ontology"

        row_od["ID"] = cell_types["FBbt_id"][i]
        row_od["obo_id"] = cell_types["FBbt_id"][i]
        row_od["synonym"] = ("adult antennal lobe local neuron type %s of neuroblast %s"
                             % (shortname_splitter(np_type)[2], NEUROBLASTS["name"][shortname_splitter(np_type)[0]]))
        row_od["label"] = "adult antennal lobe local neuron %s" % np_type
        row_od["Xref_def"] = cell_types["ref"][i]
        row_od["creation_date"] = cell_types["date"][i]
        row_od["neuroblast"] = NEUROBLASTS["ID"][shortname_splitter(np_type)[0]]

        if cell_types.notnull()["glomeruli"][i]:
            glom_list = str(cell_types["glomeruli"][i]).split(sep="|")
        else:
            glom_list = []

        row_od["definition"] = definition_maker(
            shortname=np_type, laterality=cell_types["laterality"][i],
            pattern=cell_types["pattern"][i], glomeruli=glom_list,
        )

        if glom_list:
            row_od["glomeruli"] = "|".join([glomeruli_dict[g] for g in glom_list])
        if cell_types["pattern"][i] in PATTERNS_DICT:
            row_od["arbor_type"] = PATTERNS_DICT[cell_types["pattern"][i]]
        if "Notch OFF" in row_od["definition"]:
            row_od["hemilineage"] = "FBbt:00049540"
        elif "Notch ON" in row_od["definition"]:
            row_od["hemilineage"] = "FBbt:00049539"

        template = pd.concat([template, pd.DataFrame.from_records([row_od])], ignore_index=True, sort=False)

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
