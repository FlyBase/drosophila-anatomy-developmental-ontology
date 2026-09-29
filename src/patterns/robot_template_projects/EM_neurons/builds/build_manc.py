#!/usr/bin/env python3
"""Build the MANC neuron-term ROBOT template (offline, from committed data).

Reads the committed MANC typing data (sources/manc/typing_info.tsv) plus the
curated FBbt mapping TSVs, and writes a ROBOT template. No network/token.

Usage:
    python3 build_manc.py [--out <template.tsv>]
"""

import argparse
import ast
import os
import re
import sys
from collections import OrderedDict

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import EM_common as em  # noqa: E402

REFS = " (Takemura et al., 2024; Marin et al., 2024)."


def _src(*parts):
    """Path to a file in sources/manc/."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "sources", "manc", *parts))


def cv_lookup(term, mapping):
    try:
        fbbt_id = mapping.loc[term, "FBbt_id"]
    except Exception:
        return None
    return fbbt_id if isinstance(fbbt_id, str) else None


def label_lookup(term, mapping):
    try:
        fbbt_label = mapping.loc[term, "FBbt_name"]
    except Exception:
        return None
    return fbbt_label.removeprefix("adult ") if isinstance(fbbt_label, str) else None


SHORT_TYPES = {
    "AN": "ascending neuron", "DN": "descending neuron",
    "EA": "efferent ascending neuron", "EN": "efferent neuron",
    "MN": "motor neuron", "SN": "sensory neuron",
    "SA": "sensory ascending neuron", "IN": "intrinsic neuron",
}

TEMPLATE_HEAD = OrderedDict([
    ("ID", "ID"), ("TYPE", "TYPE"), ("Label", "LABEL"),
    ("Exact_synonym", "A oboInOwl:hasExactSynonym"),
    ("Exact_syn_xref", ">A oboInOwl:hasDbXref"),
    ("Narrow_synonyms", "A oboInOwl:hasNarrowSynonym SPLIT=|"),
    ("Narrow_syn_xref", ">A oboInOwl:hasDbXref"),
    ("obo_id", "A oboInOwl:id"), ("obo_namespace", "A oboInOwl:hasOBONamespace"),
    ("Definition", "A IAO:0000115"),
    ("Def_xrefs", ">A oboInOwl:hasDbXref SPLIT=|"), ("Comment", "A rdfs:comment"),
    ("Creator", "AI dc:contributor"),
    ("Date", "AT dc:date^^xsd:dateTime"),
    ("Soma", "SC RO:0002100 some %"), ("Parents", "SC % SPLIT=|"),
    ("Lineage", "SC RO:0002202 some %"), ("Laterality", "SC RO:0000053 some %"),
    ("Projection_bundles", "SC RO:0002101 some % SPLIT=|"),
    ("Neurotransmitter", "SC RO:0002215 some %"),
    ("Presynapses", "SC RO:0013003 some % SPLIT=|"),
    ("Postsynapses", "SC RO:0013002 some % SPLIT=|"),
    ("Sens_dend", "SC RO:0013007 some % SPLIT=|"),
])


def build_template():
    new_cell_FBbt_ids = pd.read_csv(_src("new_cell_FBbt_ids.tsv"), sep="\t", index_col="type")

    typing_info = pd.read_csv(
        _src("typing_info.tsv"), sep="\t", index_col="type",
        dtype={"defaultdict": "object", "count": "int", "type": "str"},
    )
    set_cols = typing_info.columns.drop("count")
    typing_info[set_cols] = typing_info[set_cols].map(ast.literal_eval)

    class_FBbt_map = pd.read_csv(_src("class_FBbt_map.tsv"), sep="\t", index_col="term")
    subclass_detail = pd.read_csv(_src("subclass_detail.tsv"), sep="\t", index_col="term",
                                  na_filter=False, dtype=str)
    hemilineage_notch_FBbt_map = pd.read_csv(_src("hemilineage_notch_FBbt_map.tsv"), sep="\t", index_col="term")
    hemilineage_nb_FBbt_map = pd.read_csv(_src("hemilineage_nb_FBbt_map.tsv"), sep="\t", index_col="term")
    birthtime_FBbt_map = pd.read_csv(_src("birthtime_FBbt_map.tsv"), sep="\t", index_col="term")
    nerve_FBbt_map = pd.read_csv(_src("nerve_FBbt_map.tsv"), sep="\t", index_col="term")
    neuromere_FBbt_map = pd.read_csv(_src("neuromere_FBbt_map.tsv"), sep="\t", index_col="term")
    region_FBbt_map = pd.read_csv(_src("region_FBbt_map.tsv"), sep="\t", index_col="term")
    region_FBbt_map.loc["multi", "FBbt_name"] = "multiple regions"
    tract_FBbt_map = pd.read_csv(_src("tract_FBbt_map.tsv"), sep="\t", index_col="term")
    nt_go_map = pd.read_csv(_src("nt_GO_map.tsv"), sep="\t", index_col="term")

    template = pd.DataFrame.from_dict([TEMPLATE_HEAD])

    for i in new_cell_FBbt_ids.index:
        row = OrderedDict((c, "") for c in template.columns)

        row["ID"] = new_cell_FBbt_ids["FBbt_id"][i]
        row["obo_id"] = new_cell_FBbt_ids["FBbt_id"][i]
        row["obo_namespace"] = "fly_anatomy.ontology"
        row["TYPE"] = "owl:Class"
        row["Label"] = f"adult {i} neuron"
        row["Def_xrefs"] = "doi:10.7554/eLife.97766.1|doi:10.7554/eLife.97769.1|doi:10.7554/eLife.96084.1"
        row["Comment"] = ("Uncharacterized putative cell type from Marin et al. (2024), based on "
                          "MANC v1.2.1 data (Takemura et al., 2024) from NeuPrint.")
        row["Creator"] = "https://orcid.org/0000-0002-1373-1705"
        july_additions = ["FBbt:" + str(n) for n in range(20011330, 20011361)]
        july_additions.extend(["FBbt:20004627", "FBbt:20004148", "FBbt:20004631"])
        row["Date"] = "2024-07-25T12:00:00Z" if row["ID"] in july_additions else "2024-05-10T12:00:00Z"

        synonyms = list(typing_info.loc[i, "systematicType"] - set(typing_info.index))
        if len(synonyms) == 1:
            [row["Exact_synonym"]] = synonyms
            row["Exact_syn_xref"] = "doi:10.7554/eLife.97769.1"
        elif len(synonyms) > 1:
            row["Narrow_synonyms"] = "|".join(synonyms)
            row["Narrow_syn_xref"] = "doi:10.7554/eLife.97769.1"

        Parents_list = []
        projection_bundles = []
        definition_components = []

        try:
            [cell_class] = typing_info.loc[i, "cell_class"]
        except ValueError:
            cell_class = SHORT_TYPES.get(i[0:2], "neuron")
        Parents_list.append(cv_lookup(cell_class, class_FBbt_map))
        if "neuron" not in cell_class:
            cell_class += " neuron"

        type_update = ""
        to_append = ""
        name_subclass = i[2:4]
        try:
            if subclass_detail.loc[name_subclass, "parent"]:
                Parents_list.append(subclass_detail.loc[name_subclass, "parent"])
            type_update += subclass_detail.loc[name_subclass, "type_update"]
            to_append += subclass_detail.loc[name_subclass, "append"]
        except KeyError:
            pass
        try:
            [subclass] = typing_info.loc[i, "subclass"]
            if subclass_detail.loc[subclass, "parent"]:
                Parents_list.append(subclass_detail.loc[subclass, "parent"])
            row["Laterality"] = subclass_detail.loc[subclass, "laterality"]
            type_update += " " + subclass_detail.loc[subclass, "type_update"]
            to_append += " " + subclass_detail.loc[subclass, "append"]
        except ValueError:
            pass

        first_sentence = " ".join(["Adult", type_update, cell_class,
                                   f"of the {i} group", to_append]).replace("  ", " ").strip(" ")
        first_sentence = re.sub("[ ]+", " ", first_sentence)
        first_sentence = re.sub("sensory sensory", "sensory", first_sentence)
        definition_components.append(first_sentence + REFS)

        try:
            [birthtime] = typing_info.loc[i, "birthtime"]
            Parents_list.append(cv_lookup(birthtime, birthtime_FBbt_map))
            birth_lineage = f"It is a {birthtime} neuron"
            try:
                [hemilineage] = typing_info.loc[i, "hemilineage"]
                Parents_list.append(cv_lookup(hemilineage, hemilineage_notch_FBbt_map))
                row["Lineage"] = cv_lookup(hemilineage, hemilineage_nb_FBbt_map)
                birth_lineage += f" of the {hemilineage} hemilineage"
            except ValueError:
                pass
            definition_components.append(birth_lineage + REFS)
        except ValueError:
            try:
                [hemilineage] = typing_info.loc[i, "hemilineage"]
                Parents_list.append(cv_lookup(hemilineage, hemilineage_notch_FBbt_map))
                row["Lineage"] = cv_lookup(hemilineage, hemilineage_nb_FBbt_map)
                definition_components.append(f"It belongs to the {hemilineage} hemilineage" + REFS)
            except ValueError:
                pass

        nerves = ""
        try:
            [entry_nerve] = typing_info.loc[i, "common_entryNerve"]
            projection_bundles.append(cv_lookup(entry_nerve, nerve_FBbt_map))
            nerves += f"It enters the VNC via the {label_lookup(entry_nerve, nerve_FBbt_map)}"
            exit_nerve_join = " and exits via the"
        except ValueError:
            exit_nerve_join = "It exits the VNC via the"
        if len(typing_info.loc[i, "common_exitNerve"]) > 0:
            projection_bundles.extend([cv_lookup(n, nerve_FBbt_map) for n in typing_info.loc[i, "common_exitNerve"]])
            exitnerves = list(set([label_lookup(l, nerve_FBbt_map) for l in typing_info.loc[i, "common_exitNerve"]]))
            nerves += f"{exit_nerve_join} {em.name_lister(exitnerves, sort=True)}"
        if nerves:
            definition_components.append(nerves + REFS)

        if len(typing_info.loc[i, "common_longTract"]) > 0:
            projection_bundles.extend([cv_lookup(n, tract_FBbt_map) for n in typing_info.loc[i, "common_longTract"]])
            tracts = list(set([label_lookup(l, tract_FBbt_map) for l in typing_info.loc[i, "common_longTract"]]))
            definition_components.append(f"Within the VNC it fasciculates with the {em.name_lister(tracts, sort=True)}" + REFS)

        synapses = ""
        if len(typing_info.loc[i, "common_origin"]) > 0:
            origin_ids = list(set([cv_lookup(l, region_FBbt_map) for l in typing_info.loc[i, "common_origin"]]))
            if "sensory" in cell_class:
                row["Sens_dend"] = "|".join([x for x in origin_ids if x])
            else:
                row["Postsynapses"] = "|".join([x for x in origin_ids if x])
            origin_names = list(set([label_lookup(l, region_FBbt_map) for l in typing_info.loc[i, "common_origin"]]))
            if any(origin_names):
                synapses += f"It receives input in the {em.name_lister([x for x in origin_names if x], sort=True)}"
                synapse_join = " and"
            else:
                synapse_join = "It"
        else:
            synapse_join = "It"

        if len(typing_info.loc[i, "common_target"]) > 0:
            target_ids = list(set([cv_lookup(l, region_FBbt_map) for l in typing_info.loc[i, "common_target"]]))
            row["Presynapses"] = "|".join([x for x in target_ids if x])
            target_names = list(set([label_lookup(l, region_FBbt_map) for l in typing_info.loc[i, "common_target"]]))
            if any(target_names):
                synapses += f"{synapse_join} sends output to the {em.name_lister([x for x in target_names if x], sort=True)}"
        if synapses:
            synapses = re.sub("the multiple", "multiple", synapses)
            definition_components.append(synapses + REFS)

        try:
            [neurotransmitter] = typing_info.loc[i, "celltypePredictedNt"]
            row["Neurotransmitter"] = cv_lookup(neurotransmitter, nt_go_map)
            definition_components.append(f"Its predicted neurotransmitter is {neurotransmitter} (Eckstein et al., 2024).")
            row["Def_xrefs"] += "|FlyBase:FBrf0259490"
        except ValueError:
            pass

        cell_soma = ""
        cell_count = typing_info.loc[i, "count"]
        if cell_count == 1:
            cell_soma += "There is approximately one of these cells per organism"
            soma_mod = " with its soma in"
        elif cell_count > 1:
            cell_soma += f"There are approximately {str(cell_count)} of these cells per organism"
            soma_mod = " and their somas are found in"
        else:
            raise ValueError("Cell count must be >= 1")

        try:
            [somaNeuromere] = typing_info.loc[i, "somaNeuromere"]
            row["Soma"] = cv_lookup(somaNeuromere, neuromere_FBbt_map)
            cell_soma += f"{soma_mod} the {label_lookup(somaNeuromere, neuromere_FBbt_map)}"
        except ValueError:
            if len(typing_info.loc[i, "somaNeuromere"]) > 1:
                neuromeres = list(set([label_lookup(l, neuromere_FBbt_map) for l in typing_info.loc[i, "somaNeuromere"]]))
                cell_soma += f"{soma_mod} the {em.name_lister(neuromeres, sort=True)}"
        if cell_soma:
            definition_components.append(cell_soma + REFS)

        row["Parents"] = "|".join([x for x in Parents_list if isinstance(x, str)])
        row["Projection_bundles"] = "|".join([x for x in projection_bundles if isinstance(x, str)])
        row["Definition"] = " ".join(definition_components)

        template = pd.concat([template, pd.DataFrame.from_dict([row])], ignore_index=True)

    # ROBOT issue #1105 workaround: declare TYPE for every referenced CURIE
    # (scans the header row too, so the RO:* predicates get declared).
    template = pd.concat([template, em.type_rows_for_referenced_curies(template)], ignore_index=True)
    return template


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="template.tsv", help="output template path")
    args = ap.parse_args()
    template = build_template()
    template.to_csv(args.out, sep="\t", index=False)
    print(f"Wrote {len(template)} rows -> {args.out}")


if __name__ == "__main__":
    main()
