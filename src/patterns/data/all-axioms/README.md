# Documentation of the all-axioms DOSDP Pipeline

Files in this folder will be used to make all axioms the pattern specifies: logical axioms plus the generated label, definition, synonyms and other annotations.

Generated axioms go into `../../definitions.owl` and are added alongside anything in `fbbt-edit.obo`; they never replace it. So a term filled here should not also have a label or definition in `fbbt-edit.obo`. See "Design Patterns" in `src/ontology/README-editors.md`.
