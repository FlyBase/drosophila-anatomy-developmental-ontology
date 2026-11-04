# Documentation of the logical-only DOSDP Pipeline

Files in this folder will be used to make only logical axioms (no annotations). The pattern's name, definition and synonym rules are ignored for rows here, even though the yaml has them.

Use this for terms whose label, definition etc. are maintained by hand in `fbbt-edit.obo`. Remove the term's generated logical axioms (`intersection_of`/`is_a`) from `fbbt-edit.obo` when adding it here. See "Design Patterns" in `src/ontology/README-editors.md`.
