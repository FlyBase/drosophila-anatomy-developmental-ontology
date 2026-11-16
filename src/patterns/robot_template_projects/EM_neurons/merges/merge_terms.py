"""Merge pairs of EM neuron terms that turn out to be the same cell type.

Each row of a merges table names a term to keep (the older one) and a term to
obsolete. The kept term gets the union of both terms' logical axioms,
synonyms and contributors, a definition combining both (kept term's sentences
first, then the obsoleted term's), and moves to fbbt-edit.obo. The other term
is obsoleted with replaced_by. Predicted neurotransmitters that disagree are
not asserted; the comment records them instead.

The definition rewriting assumes the kept term is FlyWire-generated (brain
sentences) and the obsoleted one MANC-generated (VNC sentences), except:
- keep_dataset male_cns: see male_cns_def;
- keep_dataset fbbt-edit with obsolete_dataset flywire: a hand-curated term
  absorbing a FlyWire term, see merge_flywire_into_edit;
- keep_dataset hemibrain: the older hemibrain-defined ID is kept, but the
  definition, axioms and comment come from the obsoleted (FlyWire or optic
  lobe) term, which is based on whole-brain data; see merge_into_hemibrain_id.

Optional columns of the merges table:
- new_label: label for the kept term, where new_name can't simply replace
  keep_name in the old label;
- unpaired = y: the kept term is an unpaired midline neuron (e.g. a VUM
  neuron) whose two descending branches MANC typed as two neurons, so the MANC
  cell count is not used. MANC neurotransmitter predictions don't include
  octopamine, so the MANC prediction is dropped too;
- drop_nt = y: don't assert the FlyWire neurotransmitter prediction (e.g. when
  the kept term has experimental evidence against it);
- matched_in: |-separated datasets (male_cns, banc, flywire, flywire_v3) in
  which the two types were matched (default male_cns|banc). flywire_v3 is
  the FlyWire annotation release v3.2.0, whose hemibrain types were revised
  by comparison with the male CNS, so it is not independent of male_cns.

    python merge_terms.py merges/flywire_manc_2026-11.tsv --out x.obo   # dry run, stanzas to x.obo
    python merge_terms.py merges/flywire_manc_2026-11.tsv --apply       # edit the repo

Run from EM_neurons/. --apply edits fbbt-edit.obo (reserialise it with
`robot convert` afterwards), the EM registry, the per-connectome source id
lists and neuron_symbols.tsv; then run `sh run.sh make refresh-EM-neurons`, or,
if the templates/ cache is stale, take the terms out of components/EM_neurons.owl
with `robot remove --term-file` (as for the 2026-11 merges), saving it as OFN
(`convert --add-prefixes component_prefixes.json --format ofn`).
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
    "optic_lobe": os.path.join(EM, "sources", "optic_lobe", "new_types.tsv"),
    "hemibrain": os.path.join(EM, "sources", "hemibrain", "new_cell_types.tsv"),
}
SIMPLE = os.path.normpath(os.path.join(ONT, "..", "..", "fbbt-simple.obo"))

# Evidence that the two types are the same: matched in the male CNS and BANC.
MATCH_DATASETS = {"male_cns": ("male CNS", "Berg et al., 2026", "doi:10.1016/j.cell.2026.08.015"),
                  "banc": ("BANC", "Bates et al., 2026", "doi:10.1038/s41586-026-10735-w"),
                  "flywire": ("FlyWire", "Schlegel et al., 2024", "FlyBase:FBrf0260535"),
                  "flywire_v3": ("FlyWire", "Schlegel et al., 2024", "FlyBase:FBrf0260535")}
FLYWIRE_V3_TEXT = ("in FlyWire annotation release v3.2.0 (Schlegel et al., 2024; Berg et al., 2026; "
                   "github.com/flyconnectome/flywire_annotations), whose hemibrain types were revised "
                   "by comparison with the male CNS")
HEMIBRAIN = ("Scheffer et al., 2020", "FlyBase:FBrf0246888")
# for citing curated definitions that only give the reference as an xref
KNOWN_REFS = {"FlyBase:FBrf0239335": "Namiki et al., 2018"}
BANC_REF = "Bates et al., 2026"
PRIMARY_NEURON = "FBbt:00047097"
DATASET_TEXT = {"manc": ("MANC", "Takemura et al., 2024; Marin et al., 2024"),
                "male_cns": ("male CNS", "Berg et al., 2026"),
                "flywire": ("FlyWire", "Schlegel et al., 2024; Dorkenwald et al., 2024"),
                "optic_lobe": ("optic lobe", "Nern et al., 2025")}
NT_NAMES = {}  # filled from the def sentences: GO id -> name
NT_CLASSES = {"FBbt:00058205", "FBbt:00058207", "FBbt:00058208"}  # adult cholinergic/GABAergic/glutamatergic neuron

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


def tidy_def(sents):
    """Tidy a merged FlyWire (or optic lobe/curated) + MANC definition, as for
    the 2026-11 FlyWire/MANC merges: join the VNC entry and output sentences,
    join post- and presynapse sentences that list the same regions, GABA in
    capitals, and for ascending neurons put the MANC soma neuromere in the
    first sentence and describe the VNC before the brain."""
    manc = DATASET_TEXT["manc"][1].split("; ")
    out = []
    for s in sents:
        b, refs = body(s), cites(s)
        prev = out[-1] if out else None
        pb = body(prev) if prev else ""
        m_out = re.match(r"^In the VNC, it sends output to (.+)$", b)
        m_enter = re.match(r"^It enters the VNC via the cervical connective(?: and fasciculates with (.+))?$", pb)
        m_pre = re.match(r"^It has presynapses in (.+)$", b)
        m_post = re.match(r"^It has postsynapses in (.+)$", pb)
        if m_out and m_enter and cites(prev) == refs:
            tract = m_enter.group(1)
            out[-1] = cite("It enters the VNC via the cervical connective"
                           + (f", fasciculating with {tract}, and" if tract else " and")
                           + f" sends output to {m_out.group(1)}", refs)
        elif m_pre and m_post and m_pre.group(1) == m_post.group(1) and cites(prev) == refs:
            out[-1] = cite(f"It has postsynapses and presynapses in {m_pre.group(1)}", refs)
        else:
            out.append(s.replace("is gaba ", "is GABA "))
    if not out or not body(out[0]).startswith("Adult ascending neuron"):
        return out
    # ascending neurons
    first_s, rest = out[0], out[1:]
    soma = next((re.match(r"^Their somas are found in the (.+)$", body(s)).group(1)
                 for s in rest if re.match(r"^Their somas are found in the (.+)$", body(s))), None)
    if soma and "with its soma in the ventral nerve cord or periphery" in first_s:
        first_s = cite(body(first_s).replace("in the ventral nerve cord or periphery",
                                             f"in the {soma} of the ventral nerve cord"), manc)
    hemi, arbors, exits, inputs, brain, other = None, None, None, None, [], []
    for s in rest:
        b = body(s)
        if b.startswith("Their somas are found"):
            continue
        if re.match(r"^It is a \w+ neuron of the .+ hemilineage$", b):
            hemi = s
        elif (m := re.match(r"^It has (\w+) VNC arbors$", b)):
            arbors = m.group(1)
        elif (m := re.match(r"^It exits the VNC via the cervical connective(?: and fasciculates with (.+))?$", b)):
            exits = m.group(1) or ""
        elif (m := re.match(r"^It receives input in (.+) and sends output to the brain$", b)):
            inputs = None if m.group(1) == "multiple regions" else m.group(1)
        elif re.match(r"^It has (?:post|pre)synapses", b):
            brain.append(cite("In the brain, it" + b[2:], cites(s)))
        else:
            other.append(s)
    vnc = None
    if arbors is not None or exits is not None:
        v = f"It has {arbors} arbors in the VNC" if arbors else "It has arbors in the VNC"
        v += f", receiving input in {inputs}," if inputs else ""
        v += " and ascends via the cervical connective"
        v += f", fasciculating with {exits}" if exits else ""
        vnc = cite(v, manc)
    return [first_s] + ([hemi] if hemi else []) + ([vnc] if vnc else []) + brain + other


def count_number(sentence):
    m = re.match(r"^There (?:is|are) (?:approximately |around )?(\w+) of these (?:cells|neurons) per (organism|hemisphere)", body(sentence))
    if not m:
        return None
    n = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}.get(m.group(1), m.group(1))
    try:
        n = int(n)
    except ValueError:
        return None
    return n * (2 if m.group(2) == "hemisphere" else 1)


def matched_in(row):
    return [d for d in (row.get("matched_in") or "male_cns|banc").split("|") if d]


def match_text(row):
    if "flywire_v3" in matched_in(row):
        rest = [d for d in matched_in(row) if d != "flywire_v3"]
        parts = [f"in the {MATCH_DATASETS[d][0]} connectome ({MATCH_DATASETS[d][1]})" for d in rest]
        return " and ".join(parts + [FLYWIRE_V3_TEXT])
    ds = [MATCH_DATASETS[d] for d in matched_in(row)]
    names = [f"{n} ({r})" for n, r, _ in ds]
    joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    return f"in the {joined} connectome" + ("s" if len(names) > 1 else "")


def match_xrefs(row):
    return [x for _, _, x in (MATCH_DATASETS[d] for d in matched_in(row))]


_ANC = None


def ancestors(t):
    """is_a ancestors of t, from fbbt-simple.obo."""
    global _ANC
    if _ANC is None:
        parents, cur = {}, None
        for line in open(SIMPLE):
            if line.startswith("id: "):
                cur = line[4:].strip()
            elif line.startswith("is_a: ") and cur and "gci_" not in line:
                parents.setdefault(cur, set()).add(line.split()[1])
        _ANC = {"parents": parents, "cache": {}}
    cache, parents = _ANC["cache"], _ANC["parents"]
    if t not in cache:
        cache[t] = set()
        for p in parents.get(t, ()):
            cache[t] |= {p} | ancestors(p)
    return cache[t]


def prune_is_a(vals):
    """Drop is_a parents that another listed parent is a subclass of."""
    return [v for v in vals if not any(v in ancestors(w) for w in vals if w != v)]


SOMA_SENT_RE = re.compile(r"^Adult [\w -]+? neuron of the \S+ group, with its soma (in .+)$")
COUNT_ANY_RE = re.compile(r"^There (?:is|are) .* (?:cells?|neurons?) ")


def merge_flywire_into_edit(row, keep, obs, symbols):
    """Merge a FlyWire-generated term (named after its hemibrain type) into a
    hand-curated fbbt-edit term. The curated definition is kept. If it has no
    FlyWire data yet, the FlyWire sentences are added after it: soma position
    (only if the kept term has no soma location), hemilineage, synapse
    locations and predicted neurotransmitter (unless the kept term has a
    different neurotransmitter or drop_nt is set). The FlyWire cell count is
    not used, as the curated term already gives one."""
    k_text, k_xrefs = split_def(first(keep, "def"))
    o_text, o_xrefs = split_def(first(obs, "def"))
    o_sents = sentences(o_text)
    rels_k = [strip_comment(v) for v in values(keep, "relationship")]
    rels_o = values(obs, "relationship")
    k_nt = {v for v in rels_k if v.startswith("RO:0002215 ")}
    o_nt = {v for v in rels_o if v.startswith("RO:0002215 ")}
    drop_nt = row.get("drop_nt") == "y" or bool(k_nt and o_nt and k_nt != o_nt)
    has_soma = any(v.startswith(SOMA_REL + " ") for v in rels_k)
    # a curated hemilineage/lineage wins over FlyWire's; a different FlyWire one goes in the comment
    has_lineage = "lineage" in k_text or any(v.startswith("RO:0002202 ") for v in rels_k)
    hemi_note = ""
    has_flywire = all(r in k_text for r in FLYWIRE_REFS)
    o_name = row["obsolete_name"]

    k_sents = sentences(k_text)
    if not any(cites(x) for x in k_sents) and len(k_xrefs) == 1 and k_xrefs[0] in KNOWN_REFS:
        k_text = " ".join(cite(x.rstrip("."), [KNOWN_REFS[k_xrefs[0]]]) for x in re.split(r"(?<=\.) ", k_text))
    add = []
    if not has_flywire:
        k_sents = re.split(r"(?<=\.) (?=[A-Z])", k_text)   # curated sentences may be uncited
        for s in o_sents:
            b = body(s)
            m = SOMA_SENT_RE.match(b)
            if m:
                if has_soma:
                    continue
                pos = re.sub(r"^in the brain, ", "", m.group(1)).replace("near to the ", "near the ")
                if k_sents and re.search(r"cell body|soma", k_sents[0]):
                    # the curated first sentence gives the soma: add the FlyWire position to it
                    # (an uncited first sentence takes the curated definition's first citation)
                    refs0 = cites(k_sents[0]) or next((cites(x) for x in k_sents if cites(x)), [])
                    k_sents[0] = cite(body(k_sents[0]).rstrip(".") + f", {pos}", refs0 + cites(s))
                else:
                    add.append(cite(f"Its soma is {m.group(1)}", cites(s)))
            elif HEMI_RE.match(b) and has_lineage:
                hl = HEMI_RE.match(b).group(1)
                words = lambda t: set(re.findall(r"[\w&]+", t))
                if not words(hl) <= words(k_text):
                    hemi_note = (f" FlyWire assigns it to the {hl} hemilineage "
                                 f"({'; '.join(FLYWIRE_REFS)}).")
            elif NT_RE.match(b):
                if not drop_nt:
                    add.append(cite(b.replace("is gaba", "is GABA"), cites(s)))
            elif COUNT_RE.match(b) or COUNT_ANY_RE.match(b):
                continue
            else:
                add.append(s)
    add = tidy_def(add)
    if add:
        # the curated cell count goes last
        k_sents = re.split(r"(?<=\.) (?=[A-Z])", k_text) if has_flywire else k_sents
        counts = [x for x in k_sents if re.match(r"^There (?:is|are) .*? of these (?:cells|neurons) per ", x)]
        k_text = " ".join([x for x in k_sents if x not in counts])
        add += counts
    text = " ".join([k_text] + add)
    xrefs = set(k_xrefs) | set(match_xrefs(row))
    if add:
        xrefs |= set(o_xrefs) - {HEMIBRAIN[1]}
        if drop_nt:
            xrefs.discard("FlyBase:FBrf0259490")   # Eckstein et al., only cited for the NT
    if "Eckstein et al., 2024" in text:
        xrefs.add("FlyBase:FBrf0259490")
    else:
        xrefs.discard("FlyBase:FBrf0259490")

    nt_note = ""
    if drop_nt and o_nt:
        o_nt_name = next((NT_RE.match(body(s)).group(1) for s in o_sents if NT_RE.match(body(s))), None)
        o_nt_name = {"gaba": "GABA"}.get(o_nt_name, o_nt_name)
        nt_note = (f" The FlyWire neurotransmitter prediction ({o_nt_name}; Eckstein et al., 2024) "
                   "is not asserted, as it disagrees with experimental data.")
    if HEMIBRAIN[1] in symbols[row["obsolete_id"]][1]:
        extra = (f"Hemibrain type {o_name} ({HEMIBRAIN[0]}), formerly a separate term ({row['obsolete_id']}) "
                 f"defined using FlyWire data ({'; '.join(FLYWIRE_REFS)}), was matched to this type "
                 f"{match_text(row)}.{nt_note}")
    else:
        extra = (f"FlyWire type {o_name} ({'; '.join(FLYWIRE_REFS)}), formerly a separate term "
                 f"({row['obsolete_id']}), was matched to this type {match_text(row)}.{nt_note}")
    extra += hemi_note
    # a FlyWire cell count that differs from the curated one goes in the comment
    fw_n = next((int(COUNT_RE.match(body(x)).group(1)) for x in o_sents
                 if COUNT_RE.match(body(x)) and COUNT_RE.match(body(x)).group(1).isdigit()), None)
    k_n = count_number(next((x for x in re.split(r"(?<=\.) (?=[A-Z])", text)
                             if "Schlegel et al., 2024" not in x and "of these" in x and "per " in x), ""))
    if fw_n and k_n and fw_n != k_n:
        extra += (f" There are {fw_n} of these cells in FlyWire ({'; '.join(FLYWIRE_REFS)}).")
    comment = (first(keep, "comment") + " " + extra).strip()

    syns = OrderedDict()
    def add_syn(v):
        syns.setdefault(re.match(r'"(.*?)"', v).group(1), v)
    for v in values(keep, "synonym") + values(obs, "synonym"):
        add_syn(v)
    add_syn(f'"{o_name}" EXACT [{symbols[row["obsolete_id"]][1].replace("|", ", ")}]')
    add_syn(f'"{first(obs, "name")}" EXACT []')
    syns.pop(first(keep, "name"), None)

    def axioms(tag):
        vals = OrderedDict()
        for v in values(keep, tag):
            vals.setdefault(strip_comment(v), None)
        for v in values(obs, tag):
            v = strip_comment(v)
            if tag == "relationship":
                if v.startswith("RO:0002215 ") and drop_nt:
                    continue
                if v.startswith(SOMA_REL + " ") and has_soma:
                    continue
                if v.startswith("RO:0002202 ") and has_lineage:
                    continue
            vals.setdefault(v, None)
        vals = sorted(vals)
        if tag == "is_a":   # keep the curated parents; add only non-redundant FlyWire ones
            kept = {strip_comment(v) for v in values(keep, "is_a")}
            vals = [v for v in vals if v in kept or v in prune_is_a(vals)]
        if tag == "relationship":
            for rel, generic in GENERIC_REGIONS:
                if any(v.startswith(rel + " ") and v != f"{rel} {generic}" for v in vals):
                    vals = [v for v in vals if v != f"{rel} {generic}"]
        return vals

    contributors = OrderedDict()
    for v in values(keep, "property_value") + values(obs, "property_value"):
        if "terms/contributor" in v:
            contributors.setdefault(v.replace("http://orcid.org/", "https://orcid.org/"), None)
    other_pv = [v for v in values(keep, "property_value")
                if "terms/contributor" not in v]
    st = [("id", row["keep_id"]), ("name", first(keep, "name")),
          ("def", '"%s" [%s]' % (text, ", ".join(sorted(xrefs)))), ("comment", comment)]
    st += [("subset", v) for v in OrderedDict.fromkeys(values(keep, "subset") + values(obs, "subset"))]
    st += [("synonym", v) for v in syns.values()]
    st += [("xref", v) for v in OrderedDict.fromkeys(values(keep, "xref") + values(obs, "xref"))]
    st += [("is_a", v) for v in axioms("is_a")]
    st += [("relationship", v) for v in axioms("relationship")]
    st += [("property_value", v) for v in contributors] + [("property_value", v) for v in other_pv]
    return st, drop_nt and bool(o_nt)


def merge_into_hemibrain_id(row, keep, obs, symbols):
    """Keep the older hemibrain-defined ID, with its label (the male CNS name)
    unless new_name/new_label is given, but take the definition, axioms and
    comment from the obsoleted FlyWire or optic lobe term, which is based on
    whole-brain data. The hemibrain term's coarse region axioms are dropped."""
    o_text, o_xrefs = split_def(first(obs, "def"))
    k_name, o_name = row["keep_name"], row["obsolete_name"]
    new_name = row.get("new_name") or k_name
    label = row.get("new_label") or (first(obs, "name") if row.get("new_name") else first(keep, "name"))
    text = o_text.replace(f" of the {o_name} group", f" of the {new_name} group")
    text = " ".join(tidy_def(sentences(text)))
    xrefs = set(o_xrefs) | set(match_xrefs(row))
    if any(d == "flywire_v3" for d in matched_in(row)):
        xrefs.add(MATCH_DATASETS["male_cns"][2])
    if "Eckstein et al., 2024" not in text:
        xrefs.discard("FlyBase:FBrf0259490")
    o_ds, o_refs = DATASET_TEXT[row["obsolete_dataset"]]
    note = (f"Hemibrain type {k_name} ({HEMIBRAIN[0]}) was first defined as this term from hemibrain data; "
            f"{o_ds} type {o_name} ({o_refs}), formerly a separate term ({row['obsolete_id']}), "
            f"was matched to it {match_text(row)}. The definition is now based on the {o_ds} data.")
    if row.get("new_name"):
        note += f" Named {new_name} in the male CNS ({MATCH_DATASETS['male_cns'][1]})."
    comment = (first(obs, "comment") + " " + note).strip()

    syns = OrderedDict()
    def add_syn(v):
        syns.setdefault(re.match(r'"(.*?)"', v).group(1), v)
    for v in values(keep, "synonym") + values(obs, "synonym"):
        add_syn(v)
    for nm, tid in ((k_name, row["keep_id"]), (o_name, row["obsolete_id"])):
        if nm != new_name:
            add_syn(f'"{nm}" EXACT [{symbols[tid][1].replace("|", ", ")}]')
    for lab in (first(keep, "name"), first(obs, "name")):
        add_syn(f'"{lab}" EXACT []')
    for nm in (label, new_name):
        syns.pop(nm, None)
    # an existing RELATED synonym for a name that is now EXACT
    for nm in (k_name, o_name):
        if nm in syns and " RELATED " in syns[nm] and nm != new_name:
            syns[nm] = syns[nm].replace(" RELATED ", " EXACT ")

    def axioms(tag):
        vals = OrderedDict((strip_comment(v), None) for v in values(obs, tag))
        if tag == "is_a":
            for v in values(keep, tag):
                v = strip_comment(v)
                if v not in GENERIC_PARENTS:
                    vals.setdefault(v, None)
        vals = sorted(vals)
        return prune_is_a(vals) if tag == "is_a" else vals

    contributors = OrderedDict()
    for v in values(keep, "property_value") + values(obs, "property_value"):
        if "terms/contributor" in v:
            contributors.setdefault(v.replace("http://orcid.org/", "https://orcid.org/"), None)
    other_pv = [v for v in values(keep, "property_value") if "terms/contributor" not in v]
    st = [("id", row["keep_id"]), ("name", label),
          ("def", '"%s" [%s]' % (text, ", ".join(sorted(xrefs)))), ("comment", comment)]
    st += [("synonym", v) for v in syns.values()]
    st += [("xref", v) for v in OrderedDict.fromkeys(values(keep, "xref") + values(obs, "xref"))]
    st += [("is_a", v) for v in axioms("is_a")]
    st += [("relationship", v) for v in axioms("relationship")]
    st += [("property_value", v) for v in contributors] + [("property_value", v) for v in other_pv]
    return st, False


def merge(row, keep, obs, symbols):
    if row["keep_dataset"] == "fbbt-edit" and row["obsolete_dataset"] == "flywire":
        return merge_flywire_into_edit(row, keep, obs, symbols)
    if row["keep_dataset"] == "hemibrain":
        return merge_into_hemibrain_id(row, keep, obs, symbols)
    k_text, k_xrefs = split_def(first(keep, "def"))
    o_text, o_xrefs = split_def(first(obs, "def"))
    k_sents, o_sents = sentences(k_text), sentences(o_text)
    new_name = row["new_name"]
    k_label = first(keep, "name")
    label = row.get("new_label") or (k_label.replace(row["keep_name"], new_name) if new_name else k_label)
    unpaired = row.get("unpaired") == "y"
    if new_name:
        k_sents = [s.replace(f" {row['keep_name']} ", f" {new_name} ") for s in k_sents]

    # neurotransmitter
    k_go, k_nt = nt_of(keep, k_sents)
    o_go, o_nt = nt_of(obs, o_sents)
    if unpaired:   # MANC predictions don't include octopamine: don't use them
        o_go = o_nt = None
        o_sents = [s for s in o_sents if not NT_RE.match(s)]
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
    if unpaired:
        on, o_soma = None, None
        tail = [t for t in tail if not t.startswith("Their somas")]
        tail.append(cite("There is one of these cells per organism",
                         [MATCH_DATASETS[d][1] for d in matched_in(row)]))
    elif kn and on and kn == on:
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
        k_count = [s for s in head if COUNT_ANY_RE.match(body(s))]
        head = [s for s in head if s not in k_count]
        if k_count and not unpaired:
            # a kept count in another form (e.g. per hemisphere): keep it, and
            # the MANC count only if it differs
            same = on and count_number(k_count[0]) == int(on)
            tail = [t for t in tail if not (same and "(MANC)" in t)] + k_count
        text = " ".join(tidy_def(head + vnc_sentences(o_sents) + tail))
    xrefs = set(k_xrefs) | set(o_xrefs) | set(match_xrefs(row)) | set(extra_xrefs)
    if "Eckstein et al., 2024" not in text:
        xrefs.discard("FlyBase:FBrf0259490")
    xrefs = sorted(xrefs)

    o_ds, o_refs = DATASET_TEXT[row["obsolete_dataset"]]
    comment = first(keep, "comment")
    extra = (f"{o_ds} type {row['obsolete_name']} ({o_refs}), formerly a separate term "
             f"({row['obsolete_id']}), was matched to this type {match_text(row)}. "
             f"VNC annotations are from {o_ds} v1.2.1 data ({o_refs}).")
    if new_name:
        k_ds, k_refs = DATASET_TEXT[row["keep_dataset"]]
        extra += f" Named {row['keep_name']} in {k_ds} ({k_refs})."
    if row["keep_dataset"] == "male_cns":
        extra = extra.replace(f"VNC annotations are from {o_ds} v1.2.1 data",
                              f"VNC tract and cell count are from {o_ds} v1.2.1 data")
    if unpaired:
        extra += (f" This is an unpaired neuron with two descending branches, which {o_ds} types "
                  f"as two {row['obsolete_name']} neurons ({o_refs}). The {o_ds} neurotransmitter "
                  "prediction is not used, as it does not include octopamine.")
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
            if unpaired and v in [strip_comment(w) for w in values(obs, tag)] \
                    and (v.startswith("RO:0002215 ") or v in NT_CLASSES):
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
            vals = prune_is_a(vals)
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
    other_pv = [v for v in values(keep, "property_value") if "terms/contributor" not in v]

    st = [("id", row["keep_id"]), ("name", label),
          ("def", '"%s" [%s]' % (text, ", ".join(xrefs))), ("comment", comment)]
    st += [("subset", v) for v in OrderedDict.fromkeys(values(keep, "subset") + values(obs, "subset"))]
    st += [("synonym", v) for v in syns.values()]
    st += [("xref", v) for v in OrderedDict.fromkeys(values(keep, "xref") + values(obs, "xref"))]
    st += [("is_a", v) for v in axioms("is_a")]
    st += [("relationship", v) for v in axioms("relationship")]
    st += [("property_value", v) for v in contributors] + [("property_value", v) for v in other_pv]
    return st, nt_conflict


def obsolete(row, obs, keep_label):
    reason = (f"Obsoleted: the same cell type as {keep_label} ({row['keep_id']}), "
              f"matched {match_text(row)}.")
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
