---
name: obsolete-term
description: Obsolete one or more FBbt terms in the fbbt-edit.obo editors file, following the house obsoletion procedure. Handles both 1:1 replacements (term_replaced_by / IAO:0100001) and non-1:1 suggestions (oboInOwl#consider). Surfaces usages in related terms and component files so the curator can decide what to update.
user-invocable: true
argument-hint: [FBbt_ID ...]
allowed-tools: Read, Edit, Write, Bash, Grep, Glob, AskUserQuestion
---

# Obsolete FBbt Terms

Obsoletes one or more terms in `src/ontology/fbbt-edit.obo`, following the procedure documented in `src/ontology/README-editors.md` ("Obsoleting terms", lines 94-112).

## Arguments

One or more FBbt IDs separated by spaces (e.g. `FBbt:00110069`). If no arguments are given, ask the user which terms to obsolete.

## Pre-flight reminder

Before making any edits, remind the user: *"FlyBase curators must be notified at least a week before term obsoletions are carried out. Confirm that this has been done (or that it is being done in parallel) before merging."* Do not block on this — the user is responsible.

## Key paths

All paths relative to the repository root.

- Editors file: `src/ontology/fbbt-edit.obo`
- Components: `src/ontology/components/*.owl`
- Neuron symbols source: `src/ontology/neuron_symbols.tsv`
- DOSDP filler TSVs: `src/patterns/data/all-axioms/*.tsv`, `src/patterns/data/logical-only/*.tsv`
- Robot template projects: `src/patterns/robot_template_projects/**/*.tsv`
- EM synonym mapping files (DO NOT remove from these — they are ID-based mappings to external datasets): `src/patterns/robot_template_projects/EM_synonyms/*.tsv`
- Historical snapshots (never edit): `fbbt/releases/**`, `fbbt/src/tags/**`

## Workflow

Process each FBbt ID in order. For each:

### Step 1: Validate and gather replacement info

1. Confirm the term exists and is not already obsolete:
   ```
   grep -n "^id: FBbt:NNNNNNN" src/ontology/fbbt-edit.obo
   ```
   Read ~20 lines of the stanza and check for `is_obsolete: true`. If already obsolete, skip and report.

2. If the user did not already specify replacement info for this ID on the command line or in the conversation, use `AskUserQuestion` to ask:
   - **Is there a 1:1 replacement?** (options: `Yes — use replaced_by`, `No — use consider`, `No replacement at all`)
   - **Replacement FBbt ID(s)** (free-text; comma-separated if multiple `consider` targets)
   - **Reason for obsoletion** (free-text; becomes the `comment`)

   Validate replacement IDs by grepping `src/ontology/fbbt-edit.obo` and `src/ontology/components/*.owl` so typos surface before any edit.

### Step 2: Rewrite the obsolete term's stanza

Re-read the stanza, then rewrite it to keep ONLY these fields (order matters):

```
[Term]
id: FBbt:NNNNNNN
name: obsolete <original label>
namespace: fly_anatomy.ontology   # only if present in original
def: "<original def>" [<original def xrefs>]
comment: <existing comment (if any), then the reason for obsoletion appended>
synonym: ... (keep all existing synonyms)
property_value: http://purl.org/dc/terms/contributor <orcid>   # keep
property_value: http://purl.org/dc/terms/date "..." xsd:dateTime   # keep
replaced_by: FBbt:XXXXXXX                        # if 1:1
consider: FBbt:XXXXXXX                           # one line per consider target
is_obsolete: true
```

In obo format, `is_obsolete: true` is the shorthand for `owl:deprecated "true"^^xsd:boolean` — the OBO→OWL conversion adds the `owl:deprecated` annotation automatically, so an editor viewing the file in Protege sees it as `owl:deprecated`. Do NOT add a separate `property_value` line for deprecation.

Remove entirely:
- All `is_a:` lines
- All `relationship:` lines
- All `intersection_of:` lines (and any other equivalent-class components: `union_of:`, `disjoint_from:`)
- `subset:` lines (e.g. `subset: cur`)
- `xref:` lines that are not `def` xrefs (def xrefs live inside the `def:` square brackets and stay)

Keep:
- `def:` and its xrefs
- All `synonym:` lines
- The contributor and date `property_value:` lines

**Comment handling:** if the stanza already has a `comment:` line, append the obsoletion reason to it (e.g. `<existing comment text> Obsoleted: <reason>.`) rather than overwriting it. A single `comment:` line is allowed in obo; do not add a second one.

Use the `Edit` tool with the full original stanza (from `[Term]` to the blank line after the last `property_value:`) as `old_string` and the rewritten stanza as `new_string`.

### Step 3: Find usages in related terms

Search the editors' file and live components for references to the obsolete ID:

```
grep -n "FBbt:NNNNNNN" src/ontology/fbbt-edit.obo
grep -rn "FBbt_NNNNNNN\|FBbt:NNNNNNN" src/ontology/components/
grep -rn "FBbt:NNNNNNN\|FBbt_NNNNNNN" src/patterns/data/ src/patterns/robot_template_projects/ src/ontology/neuron_symbols.tsv
```

Classify each hit:
- **In the obsolete term's own stanza** — expected, ignore.
- **In `is_a:` / `relationship:` / `equivalent_to:` lines of other terms in `fbbt-edit.obo`** — these are live logical references that will break. Report each with `file:line` and the referring term's ID/name.
- **In component `.owl` files** — report file and containing term if determinable.
- **In DOSDP / robot-template TSVs** — report file and row context. Per README step 4, the term must be removed from any TSV used for axiom generation (otherwise it will be re-generated on the next build).
- **In `src/patterns/robot_template_projects/EM_synonyms/*.tsv`** — report but DO NOT propose edits: these mappings are ID-based and should persist (same policy as the `move-to-edit` skill).
- **In `src/ontology/neuron_symbols.tsv`** — report; the symbol entry should usually be removed or transferred to the replacement term.

Print a consolidated **Usage report** for the term.

### Step 4: Ask before updating related items

For each actionable usage found in Step 3, use `AskUserQuestion` to ask whether to update it. Batch related questions into one `AskUserQuestion` call where possible. Suggested actions:

- **`is_a:` / `relationship:` referencing the obsolete ID**: options are `Re-point to replacement` (only offered if a 1:1 replacement exists), `Remove the axiom`, `Leave as-is (I'll handle manually)`.
- **TSV rows (DOSDP / robot template)**: options are `Delete row`, `Re-point FBbt ID to replacement` (if 1:1), `Leave as-is`.
- **`neuron_symbols.tsv` entry**: options are `Delete row`, `Move symbol to replacement ID` (if 1:1), `Leave as-is`.
- **Component `.owl` hits**: usually the user should handle these manually (they may be auto-regenerated). Report and ask, but default to `Leave as-is`.

For each approved edit, apply it with `Edit`. After editing, re-grep to confirm the old ID no longer appears where it should not.

### Step 5: Report

Summarise per term:
- ID and original label
- Obsoletion style applied (`replaced_by FBbt:X` / `consider FBbt:X, FBbt:Y` / no replacement)
- Comment used
- Files modified (editors' file + any related-term edits)
- Usages left unmodified (for the curator to review)
- Reminder that FlyBase must be notified if not already done, and that component regeneration (`sh run.sh make ...`) may be needed before commit.

## Sanity checks

Before reporting done, run:

```
grep -n "^id: FBbt:NNNNNNN" src/ontology/fbbt-edit.obo    # still present, once
grep -n "is_obsolete: true" src/ontology/fbbt-edit.obo | grep -c NNNNNNN  # (if possible) confirm
```

Re-read the rewritten stanza and verify:
- Label starts with `obsolete `
- No `is_a:`, `relationship:`, `subset:` or non-def `xref:` lines remain
- `is_obsolete: true` is present
- `replaced_by:` XOR `consider:` lines are present and match the user's choice
- `def:`, `synonym:`, `comment:`, contributor and date property_values are intact

## Troubleshooting

- **Parent/related term not found when re-pointing** — grep the full ID across `src/ontology/` and components; if still missing, report and leave as-is.
- **Multiple `consider` targets** — emit one `consider:` line per target, in numerical ID order.
- **obo vs owl deprecation** — `is_obsolete: true` in obo format is the canonical way to mark deprecation; only add an explicit `owl:deprecated` `property_value` if surrounding precedent in the file does.
- **Stanza ordering in the file** — do not move the stanza. Obsolete terms stay in their original numerical position in `fbbt-edit.obo`.
