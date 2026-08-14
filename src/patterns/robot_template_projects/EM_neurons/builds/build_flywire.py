#!/usr/bin/env python3
"""Build the FlyWire/FAFB neuron-term ROBOT template(s) (offline).

Faithful port of flywire_neurons/flywire_neurons.ipynb. Builds two row-sets:
  * "own"        -> FlyWire's own new types (flywire_neurons.owl)
  * "hemibrain"  -> hemibrain types now defined by FlyWire data, keeping their
                    hemibrain FBbt IDs (this set is merged into the hemibrain
                    component in the legacy workflow).

Reads committed/local data only: the FlyWire annotations TSV, the per-neuron
synapse .feather files, neuropil/superclass/lineage maps, and the committed
FlyWire neuropil-volume centres cache (data/flywire_neuropil_volumes.tsv) which
replaces the live fafbseg call for soma positioning. The optic-lobe mapping is
read from the sibling neuprint_optic_lobe_curation repo (as in EM_synonyms).

Usage:
    python3 build_flywire.py --which own|hemibrain|both --out template.tsv
"""

import argparse
import os
import re
import sys
from collections import OrderedDict

import numpy as np
import pandas as pd
from scipy.spatial import KDTree

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import EM_common as em  # noqa: E402


def _proj(*parts):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", *parts))


def _cache(name):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "data", name))


OPTIC_NEUROPIL_MAPPING = {"M": "medulla", "LP": "lobula plate", "L": "lobula"}
CT_MAPPING = {"C": "columnar", "T": "tangential"}
DN_MAPPING = {
    "a": "of the anterior dorsal brain", "b": "of the anterior ventral brain",
    "c": "of the pars intercerebralis", "d": "of the outside anterior cluster",
    "g": "of the gnathal ganglion", "p": "of the posterior brain", "x": "outside of the brain",
}
DN_PARENT_MAPPING = {
    "a": "FBbt:00047512", "b": "FBbt:00047513", "c": "FBbt:00047514", "d": "FBbt:00047515",
    "g": "FBbt:00047516", "p": "FBbt:00047517", "x": "FBbt:00047518",
}

TEMPLATE_HEAD = OrderedDict([
    ("ID", "ID"), ("TYPE", "TYPE"), ("Label", "LABEL"),
    ("obo_id", "A oboInOwl:id"), ("obo_namespace", "A oboInOwl:hasOBONamespace"),
    ("Definition", "A IAO:0000115"),
    ("Def_xrefs", ">A oboInOwl:hasDbXref SPLIT=|"), ("Comment", "A rdfs:comment"),
    ("RelatedSynonyms", "A oboInOwl:hasRelatedSynonym SPLIT=|"),
    ("RelatedSynonyms_xrefs", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("ExactSynonyms", "A oboInOwl:hasExactSynonym SPLIT=|"),
    ("ExactSynonyms_xrefs", ">A oboInOwl:hasDbXref SPLIT=|"),
    ("Creators", "AI dc:contributor SPLIT=|"),
    ("Date", "AT dc:date^^xsd:dateTime"),
    ("Soma", "SC RO:0002100 some %"), ("Parents", "SC % SPLIT=|"),
    ("Lineage", "SC RO:0002202 some %"), ("Bilateral", "SC RO:0000053 some %"),
    ("Neurotransmitter", "SC RO:0002215 some %"),
    ("Presynapses", "SC RO:0013003 some % SPLIT=|"),
    ("Postsynapses", "SC RO:0013002 some % SPLIT=|"),
])


class FlyWireBuilder:
    def __init__(self):
        info = pd.read_csv(_proj("EM_neurons", "sources", "flywire", "Supplemental_file1_neuron_annotations.tsv"),
                           sep="\t", low_memory=False)
        info["root_783"] = info.root_id

        ol_types = pd.read_csv(
            _proj("..", "..", "..", "..", "neuprint_optic_lobe_curation", "OL_FBbt_mapping.tsv"),
            sep="\t", low_memory=False, usecols=["OL_type", "Schlegel_type"])
        ol_map = ol_types[ol_types["Schlegel_type"].notna()]
        merged = pd.merge(info, ol_map, how="left", left_on="cell_type", right_on="Schlegel_type")
        info = merged.drop("Schlegel_type", axis=1)
        info.loc[info["cell_type"] == "CB3828", "OL_type"] = "Li34"
        info = info.drop_duplicates().reset_index(drop=True)
        self.info = info

        pre_counts = pd.read_feather(_proj("EM_neurons", "sources", "flywire", "per_neuron_neuropilv5_filtered_count_pre_783.feather"))
        post_counts = pd.read_feather(_proj("EM_neurons", "sources", "flywire", "per_neuron_neuropilv5_filtered_count_post_783.feather"))
        pre_counts = pre_counts[pre_counts.pre_pt_root_id.isin(info.root_id)].copy()
        post_counts = post_counts[post_counts.post_pt_root_id.isin(info.root_id)].copy()
        pre_counts["neuropil"] = pre_counts["neuropil"].astype("category")
        post_counts["neuropil"] = post_counts["neuropil"].astype("category")

        pre_counts["soma_side"] = pre_counts.pre_pt_root_id.map(
            info[["root_id", "side"]].drop_duplicates().set_index("root_id").side).astype("category")
        post_counts["soma_side"] = post_counts.post_pt_root_id.map(
            info[["root_id", "side"]].drop_duplicates().set_index("root_id").side).astype("category")

        pre_counts["np_side"] = "central"
        post_counts["np_side"] = "central"
        for x, y, z in [("left", "L", "ipsilateral"), ("right", "R", "ipsilateral"),
                        ("left", "R", "contralateral"), ("right", "L", "contralateral")]:
            pre_counts.loc[(pre_counts.soma_side == x) & (pre_counts.neuropil.str.contains(f"_{y}", na=False)), "np_side"] = z
            post_counts.loc[(post_counts.soma_side == x) & (post_counts.neuropil.str.contains(f"_{y}", na=False)), "np_side"] = z

        np_map = pd.read_csv(_proj("EM_neurons", "sources", "flywire", "neuropil_map.tsv"), sep="\t", dtype="str")
        pre_counts["neuropil_short"] = pre_counts.neuropil.apply(lambda x: x.replace("_L", "").replace("_R", "")).astype("category")
        post_counts["neuropil_short"] = post_counts.neuropil.apply(lambda x: x.replace("_L", "").replace("_R", "")).astype("category")
        pre_counts = pre_counts.merge(np_map[["neuropil_short", "neuropil_full", "NP_id"]], how="left", on="neuropil_short")
        post_counts = post_counts.merge(np_map[["neuropil_short", "neuropil_full", "NP_id"]], how="left", on="neuropil_short")

        post_counts["neuropil_ipsi_contra"] = post_counts.neuropil_full.astype(str)
        pre_counts["neuropil_ipsi_contra"] = pre_counts.neuropil_full.astype(str)
        for l in ("ipsilateral", "contralateral"):
            is_this = post_counts.np_side == l
            post_counts.loc[is_this, "neuropil_ipsi_contra"] = post_counts.loc[is_this, "neuropil_full"].map(lambda x: f"{x}_{l}")
            is_this = pre_counts.np_side == l
            pre_counts.loc[is_this, "neuropil_ipsi_contra"] = pre_counts.loc[is_this, "neuropil_full"].map(lambda x: f"{x}_{l}")
        self.pre_counts = pre_counts
        self.post_counts = post_counts

        self.full_names = dict(zip(np_map["neuropil_short"], np_map["neuropil_full"]))
        self.neuropil_ids = dict(zip(np_map["neuropil_short"], np_map["NP_id"]))
        self.cbr_ids = dict(zip(np_map["neuropil_short"], np_map["CBR_id"]))

        # KDTree of neuropil-volume centres from the committed cache
        # (replaces fafbseg.flywire.get_neuropil_volumes). Row order preserved
        # so np.bincount(ix).argmax() indexes the same volume as the notebook.
        nv = pd.read_csv(_cache("flywire_neuropil_volumes.tsv"), sep="\t")
        self.neuropil_names = nv["name"].tolist()
        self.neuropil_centers = nv[["x", "y", "z"]].to_numpy()
        self.np_tree = KDTree(self.neuropil_centers)

        self.superclasses = pd.read_csv(_proj("EM_neurons", "sources", "flywire", "superclasses.tsv"), sep="\t", dtype="str")
        self.lineage_map = pd.read_csv(_proj("EM_neurons", "sources", "flywire", "lineage_map.tsv"), sep="\t", dtype="str")

    # --- lookups -----------------------------------------------------------
    def get_type_annotations(self, t):
        this_type = self.info[(self.info.cell_type == t) | (self.info.hemibrain_type == t) | (self.info.OL_type == t)]
        if this_type.empty:
            raise ValueError(f"Unknown cell type: {t}")
        return this_type

    def describe_position(self, t):
        this_type = self.get_type_annotations(t)
        this_type = this_type[this_type.soma_x.notnull()]
        if this_type.empty:
            raise ValueError(f"No recorded soma positions for cell type: {t}")
        pos = this_type[["soma_x", "soma_y", "soma_z"]].values * [4, 4, 40]
        dist, ix = self.np_tree.query(pos, k=1)
        best = np.bincount(ix).argmax()
        vol_name = self.neuropil_names[best]
        vol_center = self.neuropil_centers[best]
        if vol_name.endswith("_L"):
            pos = pos[this_type.side == "right"]
        elif vol_name.endswith("_R"):
            pos = pos[this_type.side == "left"]
        d = (pos - vol_center).mean(axis=0)
        d_frac = np.abs(d) / np.abs(d).sum()
        desc = ""
        join = ""
        if d_frac[2] >= 0.4:
            desc += "posterior" if d[2] > 0 else "anterior"
            join = "-"
        if d_frac[1] >= 0.4:
            desc += join + ("ventral" if d[1] > 0 else "dorsal")
            join = "-"
        if d_frac[0] >= 0.4:
            desc += join
            if d[0] > 0:
                desc += "lateral" if vol_name.endswith("L") else "medial"
            else:
                desc += "medial" if vol_name.endswith("L") else "lateral"
        if not desc:
            desc = "near"
        vol_clean = vol_name.replace("_R", "").replace("_L", "")
        return desc, self.full_names.get(vol_clean, vol_clean), self.cbr_ids.get(vol_clean, "FBbt:00003625")

    def get_cbr_id(self, t):
        this_type = self.get_type_annotations(t)
        if this_type.super_class.values[0] == "sensory":
            return "FBbt:00005892"
        elif this_type.super_class.values[0] == "ascending":
            return ""
        elif this_type.pos_x.notnull().any():
            return self.describe_position(t)[2]
        return "FBbt:00003625"

    def get_presynapses(self, t):
        this_type = self.get_type_annotations(t)
        if this_type.super_class.values[0] not in ("motor",):
            pre = (self.pre_counts[self.pre_counts.pre_pt_root_id.isin(this_type.root_id)]
                   .groupby(["neuropil_full", "np_side", "NP_id"], as_index=False)["count"].sum()
                   .sort_values("count", ascending=False))
            pre["frac"] = pre["count"] / pre["count"].sum()
            to = (pre["frac"].cumsum() <= 0.8).sum()
            return pre.iloc[: to + 1].reset_index(drop=True)
        raise ValueError("Cell is wrong type to get presynapses")

    def get_postsynapses(self, t):
        this_type = self.get_type_annotations(t)
        if this_type.super_class.values[0] not in ("sensory", "ascending"):
            post = (self.post_counts[self.post_counts.post_pt_root_id.isin(this_type.root_id)]
                    .groupby(["neuropil_full", "np_side", "NP_id"], as_index=False)["count"].sum()
                    .sort_values("count", ascending=False))
            post["frac"] = post["count"] / post["count"].sum()
            to = (post["frac"].cumsum() <= 0.8).sum()
            return post.iloc[: to + 1].reset_index(drop=True)
        raise ValueError("Cell is wrong type to get postsynapses")

    def get_neurotransmitter(self, t):
        this_type = self.get_type_annotations(t)
        if len(this_type.top_nt.dropna().unique()) == 1:
            nt_name = this_type.top_nt.dropna().values[0]
            return (nt_name, em.NT_TO_GO.get(nt_name, ""))
        return False

    def get_parent_ids(self, t):
        this_type = self.get_type_annotations(t)
        parent_annotations = this_type.merge(self.superclasses, how="left",
                                             on=["flow", "super_class", "cell_class", "cell_sub_class"])
        parent_ids = parent_annotations.FBbt_id.dropna().unique()
        return ["FBbt:00047095"] if len(parent_ids) == 0 else list(parent_ids)

    def get_lineage(self, t):
        this_type = self.get_type_annotations(t)
        lineages = this_type.ito_lee_hemilineage.dropna().unique()
        if len(lineages) == 1:
            this_lineage = self.lineage_map[self.lineage_map["ito_lee_hemilineage"] == lineages[0]]
            lineage_ids = this_lineage.NB_id.dropna().unique()
            return (lineages[0], lineage_ids[0]) if len(lineage_ids) == 1 else (lineages[0], "")
        return False

    def describe_cell_type(self, t):
        this_type = self.get_type_annotations(t)
        refs = "(Schlegel et al., 2024; Dorkenwald et al., 2024)"
        if this_type.super_class.values[0] == "sensory":
            soma_loc = "periphery"
        elif this_type.super_class.values[0] == "ascending":
            soma_loc = "ventral nerve cord or periphery"
        else:
            soma_loc = "brain"
            if this_type.pos_x.notnull().any():
                pos, vol, FBbt = self.describe_position(t)
                soma_loc += f", {pos} to the {vol}"
        if this_type.super_class.values[0] == "central":
            neuron_type = "brain-intrinsic"
        elif this_type.super_class.values[0] == "optic":
            neuron_type = "optic-lobe-intrinsic"
        else:
            neuron_type = this_type.super_class.values[0].replace("_", " ")
        desc = f"Adult {neuron_type} neuron of the {t} group, with its soma in the {soma_loc} {refs}. "
        lin = self.get_lineage(t)
        if lin:
            if lin[0] not in ("primary", "putative_primary"):
                desc += f"It belongs to the {lin[0].replace('_',' ').replace('  ', ' ')} hemilineage {refs}. "
            else:
                desc += f"It is a putative embryonic-born neuron {refs}. "
        try:
            post = self.get_postsynapses(t)
            if len(post) > 0:
                desc += "It has postsynapses in "
                for i, row in post.iterrows():
                    if i == (len(post) - 2):
                        join = " and "
                    elif i == (len(post) - 1):
                        join = f" {refs}. "
                    else:
                        join = ", "
                    desc += f"the {row['np_side']} {row['neuropil_full']}{join}".replace(" central", "")
        except ValueError:
            pass
        try:
            pre = self.get_presynapses(t)
            if len(pre) > 0:
                desc += "It has presynapses in "
                for i, row in pre.iterrows():
                    if i == (len(pre) - 2):
                        join = " and "
                    elif i == (len(pre) - 1):
                        join = f" {refs}. "
                    else:
                        join = ", "
                    desc += f"the {row['np_side']} {row['neuropil_full']}{join}".replace(" central", "")
        except ValueError:
            pass
        nt = self.get_neurotransmitter(t)
        if nt:
            desc += f"Its predicted neurotransmitter is {nt[0]} (Eckstein et al., 2024). "
        if len(this_type) > 1:
            desc += f"There are approximately {len(this_type['root_id'].drop_duplicates())} of these cells per organism {refs}."
        elif len(this_type) == 1:
            desc += f"There is approximately one of these cells per organism {refs}."
        return desc.strip()

    # --- label helpers -----------------------------------------------------
    @staticmethod
    def vpn_label(cell_type):
        match = re.match(r"(([LM]{1}[P]?)([LM]?[P]?)([LM]?[P]?))([CT]{1})(e)(\d+[a-z]?)", cell_type)
        if match:
            full_neuropil, np_1, np_2, np_3, ct, em_, number = match.groups()
            neuropil = "-".join([OPTIC_NEUROPIL_MAPPING.get(n) for n in [np_1, np_2, np_3] if n])
            return f"adult {neuropil} {CT_MAPPING.get(ct)} neuron e{number}"
        return None

    @staticmethod
    def vcn_label(cell_type):
        match = re.match(r"(c)(([LM]{1}[P]?)([LM]?[P]?)([LM]?[P]?))(\d+[a-z]?)", cell_type)
        if match:
            centrifugal, full_neuropil, np_1, np_2, np_3, number = match.groups()
            neuropils = "-".join([OPTIC_NEUROPIL_MAPPING.get(n) for n in [np_1, np_2, np_3] if n])
            return f"adult {neuropils} visual centrifugal neuron {number}"
        return None

    @staticmethod
    def dn_label(cell_type):
        match = re.match(r"(DN)([abcdgpx])[e]?(\d+)", cell_type)
        if match:
            descending, region, number = match.groups()
            return (f"descending neuron {DN_MAPPING.get(region)} {cell_type}", region)
        return None

    @staticmethod
    def comma_replace(cell_type):
        return re.sub(", *", "-", cell_type)

    # --- row builders ------------------------------------------------------
    def build_own_rows(self, template):
        fw_type_ids = pd.read_csv(_proj("EM_neurons", "sources", "flywire", "FBbt_ID-cell_type.tsv"), sep="\t", dtype="str")
        for i in fw_type_ids.index:
            row = OrderedDict((c, "") for c in template.columns)
            cell_type = fw_type_ids.cell_type[i]
            row["ID"] = fw_type_ids["FBbt_id"][i]
            row["obo_id"] = fw_type_ids["FBbt_id"][i]
            row["obo_namespace"] = "fly_anatomy.ontology"
            row["TYPE"] = "owl:Class"
            row["Label"] = f"adult {self.comma_replace(cell_type)} neuron"
            row["Definition"] = self.describe_cell_type(cell_type)
            row["Def_xrefs"] = "FlyBase:FBrf0259490|FlyBase:FBrf0260535|FlyBase:FBrf0260546"
            row["Comment"] = ("Uncharacterized putative cell type from Schlegel et al. (2024), based on "
                              "FlyWire v783 (FAFB) data (Dorkenwald et al., 2024; Schlegel et al., 2024). "
                              "Soma locations are based on the closest annotated neuropil region. "
                              "Pre- or post-synapse locations are the fewest regions that collectively "
                              "contain at least 80 percent of all pre- or post-synapses of these neurons in FlyWire. "
                              "Neurotransmitter predictions are from Eckstein et al. (2024). "
                              "Other annotations are based on annotations in FlyWire and are available in "
                              "the supplemental material of Schlegel et al. (2024).")
            row["Creators"] = "https://orcid.org/0000-0002-1373-1705|https://orcid.org/0000-0002-5633-1314"
            row["Date"] = fw_type_ids["creation_date"][i]

            Parents_list = list(self.get_parent_ids(cell_type))
            if not fw_type_ids.asserted_parents.isna()[i]:
                Parents_list.extend(fw_type_ids.asserted_parents[i].split("|"))
            ExactSynonyms_list = []
            ExactSynonyms_xrefs_list = []
            RelatedSynonyms_list = []
            try:
                Synonyms_list = fw_type_ids["synonym"][i].split("|")
                if len(Synonyms_list) == 1:
                    ExactSynonyms_list = Synonyms_list
                elif len(Synonyms_list) > 1:
                    RelatedSynonyms_list = Synonyms_list
            except AttributeError:
                pass

            row["Soma"] = self.get_cbr_id(cell_type)
            nt = self.get_neurotransmitter(cell_type)
            if nt:
                row["Neurotransmitter"] = nt[1]
            lin = self.get_lineage(cell_type)
            if lin:
                row["Lineage"] = lin[1]
                if lin[0] in ("primary", "putative_primary"):
                    Parents_list.append("FBbt:00047097")
            if "contralateral" in row["Definition"]:
                row["Bilateral"] = "PATO:0000618"
            try:
                row["Presynapses"] = "|".join(self.get_presynapses(cell_type)["NP_id"].unique())
            except ValueError:
                pass
            try:
                row["Postsynapses"] = "|".join(self.get_postsynapses(cell_type)["NP_id"].unique())
            except ValueError:
                pass

            vpn = self.vpn_label(cell_type)
            if vpn:
                row["Label"] = vpn
                Parents_list.append("FBbt:00048286")
                ExactSynonyms_list.append(f"adult {cell_type} neuron")
                ExactSynonyms_xrefs_list.append("FlyBase:FBrf0260535")
            vcn = self.vcn_label(cell_type)
            if vcn:
                row["Label"] = vcn
                Parents_list.append("FBbt:00059244")
                ExactSynonyms_list.append(f"adult {cell_type} neuron")
                ExactSynonyms_xrefs_list.append("FlyBase:FBrf0260535")
            dn = self.dn_label(cell_type)
            if dn:
                row["Label"] = dn[0]
                Parents_list.append(f"{DN_PARENT_MAPPING.get(dn[1])}")

            if ("FBbt:00007440" in Parents_list) and ("FBbt:00007441" in Parents_list):
                Parents_list.remove("FBbt:00007440")
                Parents_list.remove("FBbt:00007441")
                Parents_list.append("FBbt:00067123")

            row["Parents"] = "|".join(Parents_list)
            row["ExactSynonyms"] = "|".join(ExactSynonyms_list)
            row["ExactSynonyms_xrefs"] = "|".join(ExactSynonyms_xrefs_list)
            row["RelatedSynonyms"] = "|".join(RelatedSynonyms_list)
            template = pd.concat([template, pd.DataFrame.from_dict([row])], ignore_index=True)
        return template

    def build_hemibrain_rows(self, template):
        all_hemibrain_types = pd.read_csv(_proj("EM_neurons", "sources", "hemibrain", "new_cell_types.tsv"), sep="\t", dtype="str")
        updated = all_hemibrain_types[
            all_hemibrain_types["np_type"].isin(self.info["cell_type"])
            | all_hemibrain_types["np_type"].isin(self.info["hemibrain_type"])].reset_index()
        for i in updated.index:
            row = OrderedDict((c, "") for c in template.columns)
            cell_type = updated.np_type[i]
            row["ID"] = updated["FBbt_id"][i]
            row["obo_id"] = updated["FBbt_id"][i]
            row["obo_namespace"] = "fly_anatomy.ontology"
            row["Label"] = updated["FBbt_name"][i]
            row["Definition"] = self.describe_cell_type(cell_type)
            row["Def_xrefs"] = "FlyBase:FBrf0246888|FlyBase:FBrf0259490|FlyBase:FBrf0260535|FlyBase:FBrf0260546"
            row["Comment"] = ("Uncharacterized putative cell type based on Hemibrain data (Scheffer et al., 2020) "
                              "and updated using FlyWire (FAFB) data (Dorkenwald et al., 2024; Schlegel et al., 2024). "
                              "Soma locations are based on the closest annotated neuropil region. "
                              "Pre- or post-synapse locations are the fewest regions that collectively "
                              "contain at least 80 percent of all pre- or post-synapses of these neurons in FlyWire. "
                              "Neurotransmitter predictions are from Eckstein et al. (2024). "
                              "Other annotations are based on annotations in FlyWire and are available in "
                              "the supplemental material of Schlegel et al. (2024).")
            row["Creators"] = "https://orcid.org/0000-0002-1373-1705"
            row["Date"] = updated["date"][i]
            if not updated["synonym"].isna()[i]:
                row["RelatedSynonyms"] = updated["synonym"][i]
                row["RelatedSynonyms_xrefs"] = updated["synonym_ref"][i]
            Parents_list = list(self.get_parent_ids(cell_type))
            if not updated.asserted_parents.isna()[i]:
                Parents_list.extend(updated.asserted_parents[i].split("|"))
            row["Soma"] = self.get_cbr_id(cell_type)
            nt = self.get_neurotransmitter(cell_type)
            if nt:
                row["Neurotransmitter"] = nt[1]
            lin = self.get_lineage(cell_type)
            if lin:
                row["Lineage"] = lin[1]
                if lin[0] in ("primary", "putative_primary"):
                    Parents_list.append("FBbt:00047097")
            try:
                row["Presynapses"] = "|".join(self.get_presynapses(cell_type)["NP_id"].unique())
            except ValueError:
                pass
            try:
                row["Postsynapses"] = "|".join(self.get_postsynapses(cell_type)["NP_id"].unique())
            except ValueError:
                pass
            if ("FBbt:00007440" in Parents_list) and ("FBbt:00007441" in Parents_list):
                Parents_list.remove("FBbt:00007440")
                Parents_list.remove("FBbt:00007441")
                Parents_list.append("FBbt:00067123")
            row["Parents"] = "|".join(Parents_list)
            template = pd.concat([template, pd.DataFrame.from_dict([row])], ignore_index=True)
        return template


def build_template(which):
    b = FlyWireBuilder()
    template = pd.DataFrame.from_dict([TEMPLATE_HEAD])
    if which in ("own", "both"):
        template = b.build_own_rows(template)
    if which in ("hemibrain", "both"):
        template = b.build_hemibrain_rows(template)
    template = pd.concat([template, em.type_rows_for_referenced_curies(template)], ignore_index=True)
    return template


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--which", choices=["own", "hemibrain", "both"], default="own")
    ap.add_argument("--out", default="template.tsv")
    args = ap.parse_args()
    template = build_template(args.which)
    template.to_csv(args.out, sep="\t", index=False)
    print(f"Wrote {len(template)} rows ({args.which}) -> {args.out}")


if __name__ == "__main__":
    main()
