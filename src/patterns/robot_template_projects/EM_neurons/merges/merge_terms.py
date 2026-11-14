"""Merge pairs of EM neuron terms that turn out to be the same cell type.

Each row of a merges table names a term to keep (the older one) and a term to
obsolete. The kept term gets the union of both terms' logical axioms,
synonyms and contributors, a definition combining both (kept term's sentences
first, then the obsoleted term's), and moves to fbbt-edit.obo. The other term
is obsoleted with replaced_by. Predicted neurotransmitters that disagree are
not asserted; the comment records them instead.

The definition rewriting assumes the kept term is FlyWire-generated (brain
sentences) and the obsoleted one MANC-generated (VNC sentences).

    python merge_terms.py merges/flywire_manc_2026-11.tsv --out x.obo   # dry run, stanzas to x.obo
    python merge_terms.py merges/flywire_manc_2026-11.tsv --apply       # edit the repo

Run from EM_neurons/. --apply edits fbbt-edit.obo (reserialise it with
`robot convert` afterwards), the EM registry, the per-connectome source id
lists and neuron_symbols.tsv; then run `sh run.sh make refresh-EM-neurons`, or,
if the templates/ cache is stale, take the terms out of components/EM_neurons.owl
with `robot remove --term-file` (as for the 2026-11 merges).
"""
import argparse
import csv
import os
import re
import subprocess
import sys
import tempfile
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
EM = os.path.dirname(HERE)
ONT = os.path.normpath(os.path.join(EM, "..", "..", "..", "ontology"))
EDIT = os.path.join(ONT, "fbbt-edit.obo")
COMPONENT = os.path.join(ONT, "components", "EM_neurons.owl")
SYMBOLS = os.path.join(ONT, "neuron_symbols.tsv")
REGISTRY = os.path.join(EM, "registry", "EM_neuron_registry.tsv")
SOURCE_LISTS = {
    "flywire": os.path.join(EM, "sources", "flywire", "FBbt_ID-cell_type.tsv"),
    "manc": os.path.join(EM, "sources", "manc", "new_cell_FBbt_ids.tsv"),
    "male_cns": os.path.join(EM, "sources", "male_cns", "new_types.tsv"),
}

# Evidence that the two types are the same: matched in the male CNS and BANC.
MATCH_XREFS = ["doi:10.1016/j.cell.2026.08.015", "doi:10.1038/s41586-026-10735-w"]
MATCH_TEXT = "in the male CNS (Berg et al., 2026) and BANC (Bates et al., 2026) connectomes"
BANC_REF = "Bates et al., 2026"
PRIMARY_NEURON = "FBbt:00047097"
DATASET_TEXT = {"manc": ("MANC", "Takemura et al., 2024; Marin et al., 2024"),
                "male_cns": ("male CNS", "Berg et al., 2026"),
                "flywire": ("FlyWire", "Schlegel et al., 2024; Dorkenwald et al., 2024")}
NT_NAMES = {}  # filled from the def sentences: GO id -> name

# Generic axioms dropped when the merged term has more specific ones.
GENERIC_PARENTS = {"FBbt:00047095"}                 # adult neuron
GENERIC_REGIONS = [("RO:0013002", "FBbt:00003624"),  # receives input in adult brain
                   ("RO:0013003", "FBbt:00003624")]  # sends output to adult brain

PURL = "http://purl.obolibrary.org/obo/"


# --- OBO stanza handling -----------------------------------------------------

def parse_stanzas(text):
    """Return OrderedDict id -> list of (tag, value) for every [Term]."""
    out = OrderedDict()
    for block in text.split("\n[Term]\n")[1:]:
        block = block.split("\n\n")[0]
        lines = []
        for line in block.split("\n"):
            if not line or line.startswith("["):
                continue
            tag, _, val = line.partition(": ")
            lines.append((tag, val))
        tid = dict(lines)["id"]
        out[tid] = lines
    return out


def strip_comment(val):
    """Drop a trailing ' ! label' comment."""
    return re.sub(r" ! .*$", "", val)


def values(st, tag):
    return [v for t, v in st if t == tag]


def first(st, tag, default=""):
    v = values(st, tag)
    return v[0] if v else default


def split_def(val):
    m = re.match(r'"(.*)" \[(.*)\]$', val)
    text, xrefs = m.group(1), m.group(2)
    return text, [x.strip() for x in xrefs.split(",") if x.strip()]


def sentences(text):
    return [s for s in re.split(r"(?<=\)\.) ", text) if s]


def cites(sentence):
    m = re.search(r"\(([^()]*)\)\.$", sentence)
    return [c.strip() for c in m.group(1).split(";")] if m else []


def body(sentence):
    return re.sub(r" \([^()]*\)\.$", "", sentence)


def cite(body_text, refs):
    refs = list(dict.fromkeys(refs))
    return f"{body_text} ({'; '.join(refs)})."


# --- sentence handling -------------------------------------------------------

NT_RE = re.compile(r"^Its predicted neurotransmitter is (\w+)")
COUNT_RE = re.compile(r"^There are approximately ([\d-]+) of these cells per organism"
                      r"(?: and their somas are found in the (.+?))?$")


def nt_of(st, sents):
    gos = [strip_comment(v).split()[1] for v in values(st, "relationship")
           if v.startswith("RO:0002215 ")]
    name = next((NT_RE.match(s).group(1) for s in sents if NT_RE.match(s)), None)
    name = {"gaba": "GABA"}.get(name, name)
    return (gos[0] if gos else None), name


def vnc_sentences(sents):
    """Rewrite the obsoleted (MANC) term's sentences for the merged def."""
    out, enters, tract = [], None, None
    for s in sents:
        b, refs = body(s), cites(s)
        if b.startswith("Adult descending neuron of the") or b.startswith("Adult ascending neuron of the"):
            m = re.search(r" group with (.+)$", b)
            if m:
                out.append(cite(f"It has {m.group(1)}", refs))
        elif NT_RE.match(b) or COUNT_RE.match(b):
            continue
        elif b in ("It enters the VNC via the cervical connective",
                   "It exits the VNC via the cervical connective"):
            enters = (b, refs)
        elif b.startswith("Within the VNC it fasciculates with "):
            tract = (b[len("Within the VNC it fasciculates with "):], refs)
        elif b == "It receives input in multiple regions and sends output to multiple regions":
            continue
        elif b.startswith("It receives input in the brain and sends output to "):
            out.append(cite("In the VNC, it sends output to "
                            + b[len("It receives input in the brain and sends output to "):], refs))
        else:
            out.append(s)
    if enters and tract:
        out.insert(0, cite(f"{enters[0]} and fasciculates with {tract[0]}", enters[1] + tract[1]))
    elif enters:
        out.insert(0, cite(*enters))
    elif tract:
        out.insert(0, cite("Within the VNC it fasciculates with " + tract[0], tract[1]))
    return out


# --- merging -----------------------------------------------------------------

HEMI_RE = re.compile(r"^It belongs to the (.+) hemilineage$")
FLYWIRE_REFS = ["Schlegel et al., 2024", "Dorkenwald et al., 2024"]
FLYWIRE_XREFS = ["FlyBase:FBrf0260535", "FlyBase:FBrf0260546"]
SOMA_REL = "RO:0002100"
VNC = "FBbt:00004052"
REGION_RE = re.compile(r"^(It (?:receives input in|sends output to)) (.+)$")
_REGIONS = None


def male_cns_regions():
    """From the EM_neuropils male CNS region table and ROI hierarchy: the
    nerves and connective (fibre tracts, not synaptic regions) and the VNC
    neuropils, each as {FBbt id: name as written in defs}."""
    global _REGIONS
    if _REGIONS:
        return _REGIONS
    import json
    np_dir = os.path.join(EM, "..", "EM_neuropils")
    with open(os.path.join(np_dir, "male-cns_regions.tsv")) as f:
        rows = [r for r in csv.DictReader(f, delimiter="\t") if r["FBbt_id"]]
    roi = {r["male-cns_region"]: (r["FBbt_id"], r["FBbt_name"].replace("adult ", "")) for r in rows}
    with open(os.path.join(np_dir, "male-cns_roi_hierarchy.json")) as f:
        tree = json.load(f)

    def under(node, name, inside=False):
        inside = inside or node["name"] == name
        found = [node["name"]] if inside else []
        for c in node.get("children", []):
            found += under(c, name, inside)
        return found
    tracts = {i: n for i, n in roi.values() if re.search(r"\bconnective\b|\bnerve\b(?! cord)", n)}
    vnc_parts = {roi[r][0]: roi[r][1] for r in under(tree, "VNC")
                 if r in roi and roi[r][0] not in tracts and roi[r][0] != VNC}
    _REGIONS = tracts, vnc_parts, {n for _, n in roi.values()}
    return _REGIONS


def region_names():
    return male_cns_regions()[2]


def drop_tract_regions(sentence):
    """Rewrite a male CNS input/output sentence ("It receives input in the
    ipsilateral A and B, the contralateral C, and the D and E (refs).")
    without fibre tracts, and without the whole VNC if a VNC neuropil is
    listed. Groups are joined as in build_male_cns.py. Returns None if no
    region is left."""
    tracts, vnc_parts, _ = male_cns_regions()
    b, refs = body(sentence), cites(sentence)
    m = REGION_RE.match(b)
    if not m:
        return sentence
    # region names containing " and " are protected while splitting the lists
    anded = {n.replace(" and ", " & "): n for n in region_names() if " and " in n}
    text = m.group(2)
    for k, v in anded.items():
        text = text.replace(v, k)
    parsed = []
    for g in re.split(r",? and (?=the )|, (?=the )", text):
        g = g[len("the "):]
        lat = next((l for l in ("ipsilateral ", "contralateral ") if g.startswith(l)), "")
        parsed.append((lat, [anded.get(n, n) for n in re.split(r", | and ", g[len(lat):])]))
    names = {n for _, items in parsed for n in items}
    drop = set(tracts.values())
    if names & set(vnc_parts.values()):
        drop.add("ventral nerve cord")
    if not drop & names:
        return sentence
    parts = [f"the {lat}{name_list(kept)}" for lat, items in parsed
             if (kept := [n for n in items if n not in drop])]
    if not parts:
        return None
    joined = ", and ".join(parts) if len(parts) < 3 else f"{parts[0]}, {parts[1]}, and {parts[2]}"
    return cite(f"{m.group(1)} {joined}", refs)


def drop_tract_axioms(rels):
    """Drop input/output axioms on fibre tracts, and on the whole VNC where the
    same relation has a VNC neuropil."""
    tracts, vnc_parts, _ = male_cns_regions()
    out = []
    for v in rels:
        rel, _, obj = v.partition(" ")
        if rel in ("RO:0013002", "RO:0013003"):
            if obj in tracts:
                continue
            if obj == VNC and any(w.startswith(rel + " ") and w.split(" ")[1] in vnc_parts for w in rels):
                continue
        out.append(v)
    return out


def name_list(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


_FLYWIRE = None


def flywire_soma(cell_type):
    """(position, neuropil, cell body rind id) for a FlyWire type, from the
    FlyWire builder's soma positioning (the neuropil closest to most somas),
    or None if the type or the (untracked) FlyWire source files are missing."""
    global _FLYWIRE
    if _FLYWIRE is None:
        sys.path.insert(0, os.path.join(EM, "builds"))
        try:
            from build_flywire import FlyWireBuilder
            _FLYWIRE = FlyWireBuilder()
        except (OSError, ImportError) as e:
            print(f"FlyWire soma positions not available ({e}); skipping", file=sys.stderr)
            _FLYWIRE = False
    if not _FLYWIRE:
        return None
    try:
        return _FLYWIRE.describe_position(cell_type)
    except ValueError:
        return None


def male_cns_def(row, k_sents, o_sents, nt_conflict):
    """Merged def for a kept male CNS term (whole CNS) and an obsoleted MANC
    term: male CNS sentences, then the MANC tract and cell count, with BANC
    (optional banc_* columns of the merges table) cited where it agrees.
    Fibre tracts are dropped from the input/output sentences, and the soma
    position is added from FlyWire (optional flywire_type column, else the
    male CNS name) where available.
    Returns (sentences, notes for the comment, extra is_a parents, extra
    relationships, extra def xrefs)."""
    manc = DATASET_TEXT["manc"][1].split("; ")
    banc_hl = row.get("banc_hemilineage", "")
    banc_nt = row.get("banc_nt", "").lower()
    out, notes, parents, agree, rels, xrefs = [], [], [], [], [], []
    soma = flywire_soma(row.get("flywire_type") or row["keep_name"])
    hemi = next((HEMI_RE.match(body(s)).group(1) for s in k_sents if HEMI_RE.match(body(s))), None)
    nt_sent = None
    for s in k_sents:
        b, refs = body(s), cites(s)
        if HEMI_RE.match(b):
            if banc_hl and banc_hl.replace("_", " ") == hemi:
                refs = refs + [BANC_REF]
                agree.append("hemilineage")
            out.append(cite(b, refs))
        elif NT_RE.match(b):
            if not nt_conflict:
                if banc_nt and banc_nt == NT_RE.match(b).group(1).lower():
                    refs = refs + [BANC_REF]
                    agree.append("predicted neurotransmitter")
                nt_sent = cite(b.replace("is gaba", "is GABA"), refs)
        else:
            # "...neuron of the posterior brain of the DNp66 group" -> soma clause
            s = re.sub(r"^(Adult descending neuron) of the (.+?) of the (\S+) group ",
                       r"\1 of the \3 group, with its soma in the \2 ", s)
            if soma and ", with its soma in the " in s:
                pos, vol, cbr = soma
                s = cite(body(s) + (f", near the {vol}" if pos == "near" else f", {pos} to the {vol}"),
                         FLYWIRE_REFS + cites(s))
                rels.append(f"{SOMA_REL} {cbr}")
                xrefs += FLYWIRE_XREFS
                notes.append("Soma position is from FlyWire data, based on the closest annotated "
                             f"neuropil region ({'; '.join(FLYWIRE_REFS)}).")
            s = drop_tract_regions(s)
            if s:
                out.append(s)
            if b.startswith("Adult descending neuron of the") and not hemi and banc_hl == "putative_primary":
                out.append(cite("It is a putative embryonic-born neuron", [BANC_REF]))
                parents.append(PRIMARY_NEURON)
    # MANC: tract and count only (its input/output summary is coarser than male CNS's)
    enters = tract = None
    manc_n = None
    for s in o_sents:
        b = body(s)
        if b == "It enters the VNC via the cervical connective":
            enters = True
        elif b.startswith("Within the VNC it fasciculates with "):
            tract = b[len("Within the VNC it fasciculates with "):]
        elif COUNT_RE.match(b):
            manc_n = COUNT_RE.match(b).group(1)
    if enters:
        out.append(cite("It enters the VNC via the cervical connective"
                        + (f", fasciculating with {tract}" if tract else ""), manc))
    if nt_sent:
        out.append(nt_sent)
    counts = {"MANC": manc_n, "male CNS": row.get("male_cns_count") or None,
              "BANC": row.get("banc_count") or None}
    refs = {"MANC": manc, "male CNS": ["Berg et al., 2026"], "BANC": [BANC_REF]}
    present = {k: v for k, v in counts.items() if v}
    if len(set(present.values())) == 1:
        n = next(iter(present.values()))
        out.append(cite(f"There are approximately {n} of these cells per organism",
                        [r for k in present for r in refs[k]]))
        if "BANC" in present:
            agree.append("cell count")
    else:
        # counts differ between datasets: give the range, citing all of them
        ns = sorted({int(v) for v in present.values()})
        out.append(cite(f"There are approximately {ns[0]}-{ns[-1]} of these cells per organism",
                        [r for k in present for r in refs[k]]))
    if agree:
        listed = agree[0] if len(agree) == 1 else ", ".join(agree[:-1]) + " and " + agree[-1]
        notes.append(f"BANC data ({BANC_REF}) agree on {listed}.")
    if row.get("banc_function"):
        notes.append(f"Cell function in BANC: {row['banc_function'].replace('_', ' ')} ({BANC_REF}).")
    return out, notes, parents, rels, xrefs


def merge(row, keep, obs, symbols):
    k_text, k_xrefs = split_def(first(keep, "def"))
    o_text, o_xrefs = split_def(first(obs, "def"))
    k_sents, o_sents = sentences(k_text), sentences(o_text)
    new_name = row["new_name"]
    k_label = first(keep, "name")
    label = k_label.replace(row["keep_name"], new_name) if new_name else k_label
    if new_name:
        k_sents = [s.replace(f" {row['keep_name']} ", f" {new_name} ") for s in k_sents]

    # neurotransmitter
    k_go, k_nt = nt_of(keep, k_sents)
    o_go, o_nt = nt_of(obs, o_sents)
    nt_conflict = bool(k_go and o_go and k_go != o_go)
    nt_sent = None
    if not nt_conflict:
        nt_sent = next((s for s in k_sents + o_sents if NT_RE.match(s)), None)

    # cell counts (and MANC soma neuromere)
    def count(sents):
        for s in sents:
            m = COUNT_RE.match(body(s))
            if m:
                return m.group(1), m.group(2), cites(s)
        return None, None, []
    kn, _, krefs = count(k_sents)
    on, o_soma, orefs = count(o_sents)
    tail = []
    if o_soma:
        tail.append(cite(f"Their somas are found in the {o_soma}", orefs))
    if nt_sent:
        tail.append(nt_sent)
    if kn and on and kn == on:
        tail.append(cite(f"There are approximately {kn} of these cells per organism", krefs + orefs))
    else:
        if kn:
            tail.append(cite(f"There are approximately {kn} of these cells per organism (FlyWire)", krefs))
        if on:
            tail.append(cite(f"There are approximately {on} of these cells per organism (MANC)", orefs))

    notes, parents, rels, extra_xrefs = [], [], [], []
    if row["keep_dataset"] == "male_cns":
        sents, notes, parents, rels, extra_xrefs = male_cns_def(row, k_sents, o_sents, nt_conflict)
        text = " ".join(sents)
    else:
        head = [s for s in k_sents if not NT_RE.match(s) and not COUNT_RE.match(body(s))]
        text = " ".join(head + vnc_sentences(o_sents) + tail)
    xrefs = sorted(set(k_xrefs) | set(o_xrefs) | set(MATCH_XREFS) | set(extra_xrefs))

    o_ds, o_refs = DATASET_TEXT[row["obsolete_dataset"]]
    comment = first(keep, "comment")
    extra = (f"{o_ds} type {row['obsolete_name']} ({o_refs}), formerly a separate term "
             f"({row['obsolete_id']}), was matched to this type {MATCH_TEXT}. "
             f"VNC annotations are from {o_ds} v1.2.1 data ({o_refs}).")
    if new_name:
        k_ds, k_refs = DATASET_TEXT[row["keep_dataset"]]
        extra += f" Named {row['keep_name']} in {k_ds} ({k_refs})."
    if row["keep_dataset"] == "male_cns":
        extra = extra.replace(f"VNC annotations are from {o_ds} v1.2.1 data",
                              f"VNC tract and cell count are from {o_ds} v1.2.1 data")
    if nt_conflict:
        extra += (f" Predicted neurotransmitters differ between datasets ({k_nt} in "
                  f"{DATASET_TEXT[row['keep_dataset']][0]}, {o_nt} in {o_ds}; Eckstein et al., 2024), "
                  f"so none is asserted here.")
    if notes:
        extra += " " + " ".join(notes)
    comment = (comment + " " + extra).strip()

    # synonyms: both terms' own, plus the other dataset's name and old labels
    syns = OrderedDict()
    def add_syn(v):
        key = re.match(r'"(.*?)"', v).group(1)
        syns.setdefault(key, v)
    for v in values(keep, "synonym") + values(obs, "synonym"):
        add_syn(v)
    if new_name:
        add_syn(f'"{row["keep_name"]}" EXACT [{symbols[row["keep_id"]][1].replace("|", ", ")}]')
        add_syn(f'"{k_label}" EXACT []')
    else:
        add_syn(f'"{row["obsolete_name"]}" EXACT [{symbols[row["obsolete_id"]][1].replace("|", ", ")}]')
    add_syn(f'"{first(obs, "name")}" EXACT []')
    oname = row["obsolete_name"]
    if not new_name and " RELATED " in syns.get(oname, ""):
        refs = re.search(r"\[(.*)\]", syns[oname]).group(1).split(", ")
        refs += symbols[row["obsolete_id"]][1].split("|")
        syns[oname] = f'"{oname}" EXACT [{", ".join(sorted(set(r for r in refs if r)))}]'
    syns.pop(label, None)
    syns.pop(new_name or row["keep_name"], None)

    def axioms(tag):
        vals = OrderedDict()
        for v in values(keep, tag) + values(obs, tag):
            v = strip_comment(v)
            if tag == "relationship" and nt_conflict and v.startswith("RO:0002215 "):
                continue
            vals.setdefault(v, None)
        if tag == "is_a":
            for p in parents:
                vals.setdefault(p, None)
        if tag == "relationship":
            for r in rels:
                vals.setdefault(r, None)
        vals = sorted(vals)
        # drop generic axioms the other term makes redundant
        if tag == "is_a" and len(vals) > 1:
            vals = [v for v in vals if v not in GENERIC_PARENTS]
        if tag == "relationship":
            for rel, generic in GENERIC_REGIONS:
                if any(v.startswith(rel + " ") and v != f"{rel} {generic}" for v in vals):
                    vals = [v for v in vals if v != f"{rel} {generic}"]
            if row["keep_dataset"] == "male_cns":
                vals = drop_tract_axioms(vals)
        return vals

    contributors = OrderedDict()
    for v in values(keep, "property_value") + values(obs, "property_value"):
        if "terms/contributor" in v:
            contributors.setdefault(v.replace("http://orcid.org/", "https://orcid.org/"), None)
    date = next(v for v in values(keep, "property_value") if "terms/date" in v)

    st = [("id", row["keep_id"]), ("name", label),
          ("def", '"%s" [%s]' % (text, ", ".join(xrefs))), ("comment", comment)]
    st += [("subset", v) for v in OrderedDict.fromkeys(values(keep, "subset") + values(obs, "subset"))]
    st += [("synonym", v) for v in syns.values()]
    st += [("xref", v) for v in OrderedDict.fromkeys(values(keep, "xref") + values(obs, "xref"))]
    st += [("is_a", v) for v in axioms("is_a")]
    st += [("relationship", v) for v in axioms("relationship")]
    st += [("property_value", v) for v in contributors] + [("property_value", date)]
    return st, nt_conflict


def obsolete(row, obs, keep_label):
    reason = (f"Obsoleted: the same cell type as {keep_label} ({row['keep_id']}), "
              f"matched {MATCH_TEXT}.")
    comment = (first(obs, "comment") + " " + reason).strip()
    st = [("id", row["obsolete_id"]), ("name", "obsolete " + first(obs, "name")),
          ("def", first(obs, "def")), ("comment", comment)]
    st += [("synonym", v) for v in values(obs, "synonym")]
    st += [("property_value", v) for v in values(obs, "property_value")
           if "terms/contributor" in v or "terms/date" in v]
    st += [("is_obsolete", "true"), ("replaced_by", row["keep_id"])]
    return st


def render(st):
    return "[Term]\n" + "\n".join(f"{t}: {v}" for t, v in st) + "\n"


# --- I/O ---------------------------------------------------------------------

def extract_component_terms(ids):
    with tempfile.TemporaryDirectory() as tmp:
        terms = os.path.join(tmp, "terms.txt")
        out = os.path.join(tmp, "terms.obo")
        with open(terms, "w") as f:
            f.write("\n".join(PURL + i.replace(":", "_") for i in ids) + "\n")
        subprocess.run(["robot", "filter", "--input", COMPONENT, "--term-file", terms,
                        "--signature", "true", "--trim", "false",
                        "convert", "--output", out], check=True)
        return parse_stanzas(open(out).read())


def drop_rows(path, column, ids):
    with open(path) as f:
        lines = f.read().split("\n")
    header = lines[0].split("\t")
    col = header.index(column)
    kept = [lines[0]] + [l for l in lines[1:] if not l or l.split("\t")[col] not in ids]
    with open(path, "w") as f:
        f.write("\n".join(kept))
    return len(lines) - len(kept)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("merges")
    ap.add_argument("--out", default=None, help="also write the stanzas to this file, for review")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.merges), delimiter="\t"))
    edit_text = open(EDIT).read()
    edit = parse_stanzas(edit_text)
    ids = [r[c] for r in rows for c in ("keep_id", "obsolete_id")]
    comp = extract_component_terms([i for i in ids if i not in edit])
    symbols = {r["FBbt_id"]: (r["symbol"], r["reference"])
               for r in csv.DictReader(open(SYMBOLS), delimiter="\t")}

    merged, obsoleted, conflicts = [], [], []
    for r in rows:
        keep = edit.get(r["keep_id"]) or comp[r["keep_id"]]
        obs = edit.get(r["obsolete_id"]) or comp[r["obsolete_id"]]
        st, conflict = merge(r, keep, obs, symbols)
        merged.append(st)
        obsoleted.append(obsolete(r, obs, dict(st)["name"]))
        if conflict:
            conflicts.append(r["keep_id"])

    if args.out:
        with open(args.out, "w") as f:
            f.write("\n".join(render(s) for s in merged + obsoleted))
    print(f"{len(merged)} merged, {len(obsoleted)} obsoleted, "
          f"{len(conflicts)} NT conflicts", file=sys.stderr)

    if not args.apply:
        return

    # fbbt-edit.obo: replace stanzas already there, append the rest before the
    # first [Typedef] (robot convert puts them in ID order)
    for st in merged + obsoleted:
        tid = dict(st)["id"]
        new = render(st)
        m = re.search(r"\n\[Term\]\nid: %s\n.*?\n\n" % re.escape(tid), edit_text, re.S)
        if m:
            edit_text = edit_text[:m.start()] + "\n" + new + "\n" + edit_text[m.end():]
        else:
            i = edit_text.index("\n[Typedef]\n")
            edit_text = edit_text[:i] + "\n" + new + edit_text[i:]
    with open(EDIT, "w") as f:
        f.write(edit_text)

    gone = {r[c] for r in rows for c in ("keep_id", "obsolete_id")}
    print(f"registry: {drop_rows(REGISTRY, 'FBbt_id', gone)} rows removed", file=sys.stderr)
    for ds, path in SOURCE_LISTS.items():
        col = open(path).readline().rstrip("\n").split("\t")
        col = next(c for c in col if c.lower().replace(":", "_") in ("fbbt_id", "id", "fbbt"))
        print(f"{ds} source: {drop_rows(path, col, gone)} rows removed", file=sys.stderr)

    # neuron_symbols.tsv: drop the obsoleted terms' symbols; a renamed kept
    # term takes the obsoleted term's symbol and reference
    renames = {r["keep_id"]: r["obsolete_id"] for r in rows if r["new_name"]}
    lines = open(SYMBOLS).read().split("\n")
    obs_ids = {r["obsolete_id"] for r in rows}
    out_lines = []
    for l in lines:
        f = l.split("\t")
        if len(f) > 1 and f[1] in obs_ids:
            continue
        if len(f) > 1 and f[1] in renames:
            s, ref = symbols[renames[f[1]]]
            l = "\t".join([s, f[1], ref])
        out_lines.append(l)
    with open(SYMBOLS, "w") as fh:
        fh.write("\n".join(out_lines))


if __name__ == "__main__":
    main()
