# FBbt (Drosophila anatomy ontology)

Editing conventions are in [src/ontology/README-editors.md](src/ontology/README-editors.md); read it before editing. In particular:
- "Serialisation": reserialise `fbbt-edit.obo` with `robot convert` before committing if it was edited outside Protege.
- "Continuous Integration": what CI checks and how to run them locally.
- "Design Patterns": filler tsvs in `src/patterns/data/logical-only` generate only logical axioms, even when the pattern has name/def rules; `all-axioms` generates everything. Generated axioms are imported from `definitions.owl` alongside `fbbt-edit.obo` and never change it.

Repo skills are in `.claude/skills/` (`/move-to-edit`, `/obsolete-term`).
