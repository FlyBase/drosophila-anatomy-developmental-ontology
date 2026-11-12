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
}

# Evidence that the two types are the same: matched in the male CNS and BANC.
MATCH_XREFS = ["doi:10.1016/j.cell.2026.08.015", "doi:10.1038/s41586-026-10735-w"]
MATCH_TEXT = "in the male CNS (Berg et al., 2026) and BANC (Bates et al., 2026) connectomes"
DATASET_TEXT = {"manc": ("MANC", "Takemura et al., 2024; Marin et al., 2024"),
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

    head = [s for s in k_sents if not NT_RE.match(s) and not COUNT_RE.match(body(s))]
    text = " ".join(head + vnc_sentences(o_sents) + tail)
    xrefs = sorted(set(k_xrefs) | set(o_xrefs) | set(MATCH_XREFS))

    o_ds, o_refs = DATASET_TEXT[row["obsolete_dataset"]]
    comment = first(keep, "comment")
    extra = (f"{o_ds} type {row['obsolete_name']} ({o_refs}), formerly a separate term "
             f"({row['obsolete_id']}), was matched to this type {MATCH_TEXT}. "
             f"VNC annotations are from {o_ds} v1.2.1 data ({o_refs}).")
    if new_name:
        k_ds, k_refs = DATASET_TEXT[row["keep_dataset"]]
        extra += f" Named {row['keep_name']} in {k_ds} ({k_refs})."
    if nt_conflict:
        extra += (f" Predicted neurotransmitters differ between datasets ({k_nt} in FlyWire, "
                  f"{o_nt} in {o_ds}; Eckstein et al., 2024), so none is asserted here.")
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
    syns.pop(label, None)
    syns.pop(new_name or row["keep_name"], None)

    def axioms(tag):
        vals = OrderedDict()
        for v in values(keep, tag) + values(obs, tag):
            v = strip_comment(v)
            if tag == "relationship" and nt_conflict and v.startswith("RO:0002215 "):
                continue
            vals.setdefault(v, None)
        vals = sorted(vals)
        # drop generic axioms the other term makes redundant
        if tag == "is_a" and len(vals) > 1:
            vals = [v for v in vals if v not in GENERIC_PARENTS]
        if tag == "relationship":
            for rel, generic in GENERIC_REGIONS:
                if any(v.startswith(rel + " ") and v != f"{rel} {generic}" for v in vals):
                    vals = [v for v in vals if v != f"{rel} {generic}"]
        return vals

    contributors = OrderedDict()
    for v in values(keep, "property_value") + values(obs, "property_value"):
        if "terms/contributor" in v:
            contributors.setdefault(v, None)
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
