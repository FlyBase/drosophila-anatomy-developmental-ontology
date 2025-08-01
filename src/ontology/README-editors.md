These notes are for the EDITORS of FBbt

This project uses the [ontology development kit](https://github.com/INCATools/ontology-development-kit) (ODK).

For more details on ontology management, please see the [OBO tutorial](https://github.com/jamesaoverton/obo-tutorial) or the [Gene Ontology Editors Tutorial](https://go-protege-tutorial.readthedocs.io/en/latest/).

You may also want to read the [GO ontology editors guide](http://go-ontology.readthedocs.org/).

# Requirements and Setup

You will need to install:
 1. [Protege](https://protege.stanford.edu/) (for editing)
 2. A git client (we assume command line git)
 3. [docker](https://www.docker.com/get-docker) (for using ODK)

## Protege Setup

To set up Protege, see [Protege 5.6 setup for GO](https://wiki.geneontology.org/Protege5_6_setup_for_GO_Eds) for main steps.

Under `New Entities Metadata` set:

- Creator property = `http://purl.org/dc/terms/contributor`
- Creator value = `Use ORCID`
- Date property = `http://purl.org/dc/terms/date`
- Date value format = `ISO-8601`

Under `User details` add your ORCID (register at https://orcid.org if you do not have one).

## ODK Setup

#### Configuration

ODK can be configured by setting options in `fbbt-odk.yaml`. See [ODK Project Configuration Schema](https://github.com/INCATools/ontology-development-kit/blob/master/docs/project-schema.md) for details. Update the repo (see below) after making changes.

#### Updating

To get the latest version of ODK, run: `docker pull obolibrary/odkfull`

To update the repo (Makefile etc.), run: `sh run.sh update_repo`

#### Makefile Notes

NEVER edit the [Makefile](Makefile) - this file is managed by the ODK and will be replaced when the repo is updated.

For changing the the pipeline, edit [fbbt.Makefile](fbbt.Makefile) - everything added here will override instructions in the other Makefile.

## ID Ranges

These are stored in the file [fbbt-idranges.owl](fbbt-idranges.owl). If you do not have an ID range, get one from the maintainer of this repo.

** ONLY USE IDs WITHIN YOUR RANGE!! **

Protege can read the idranges file and automate term ID management.

# Editing the Ontology

First, clone the repository:

`git clone https://github.com/FlyBase/drosophila-anatomy-developmental-ontology.git`

Make sure you have an ID range in the [idranges file](fbbt-idranges.owl) (see above).

There are multiple places that axioms can be edited:
1. Editors' file
2. Design patterns
3. Robot templates
4. Neuron symbols
5. SSSOM mappings
6. Extended logical axioms

Changes should be made on a branch and merged via a Pull Request (PR) after travis checks have passed (see below). If your changes relate to an issue, link the PR to the issue using 'related to #' or 'fixes #' as appropriate in the PR description.


## Editors' File

The editors' file, [fbbt-edit.obo](fbbt-edit.obo), consists of axioms that are manually maintained.

#### Definitions

Text definitions should state the parent (or other appropriate higher level) class and ideally provide enough description for users to discriminate between this and similar entities. In practice, imperfect knowledge can make this difficult. Logical axioms should be reflected in the definition with citations.

Inline (Author, year) citations should be added to the text, and publication IDs should be added as xrefs. Xrefs should be `http://www.geneontology.org/formats/oboInOwl#hasDbXref` meta-annotations using FlyBase FBrf IDs (prefixed with `FlyBase:`), or dois (prefixed with `doi:`) where FBrfs are unavailable.

For a term with a logical (equivalent class) definition, leaving the text definition as '.' in the editors' file will result in a text definition being automatically generated based on the logical definition during the release process. If there are no other available references, `FBC:Autogenerated` can be used as an xref in this case (to be added manually).

#### Labels and Synonyms

The main identifying part of the label should be used in at least one of the definition xrefs. This should be extended with context such as stage or location if needed for clarification (e.g. `calyx of oviduct`, `calyx of adult mushroom body`). Labels should ideally spell out all words, but abbreviations can be used to avoid unreasonably long labels, especially if they are in common usage (such as `VNC`).

Stages in labels refer to the entity, rather than the organism as a whole, therefore a `larval` entity may exist in the embryo, larva or pupa, if it is essentially the same as that found in the larva. Similarly, `adult` entities may also exist during the pupal stage. `embryonic` and `pupal` classes should only be created for entities that are different to what is found in the larva or adult. If a class is intended to represent entities that may exist during `larval` or `adult` stages, these should not have a stage specified in the label (and should not have a `part of` relationship to any stage-specific terms).

Other names from the literature should be recorded as synonyms, with publication IDs added as xrefs. Variants of these names that could help user searches can also be added as synonyms. See [obook](https://oboacademy.github.io/obook/reference/synonyms-properties/) for information about different synonym scopes.

#### Obsoleting terms

Notify Flybase curators at least a week before carrying out any term obsoletions, linking to the relevant GitHub issue.

Edits to the obsolete term:

1. Add `obsolete` the start of the label.
2. Add the reason for the obsoletion as a comment.
3. If there is a 1:1 replacement term, add its ID as a `http://purl.obolibrary.org/obo/IAO_0100001` (`term_replaced_by`) annotation, otherwise add any replacement term IDs as `http://www.geneontology.org/formats/oboInOwl#consider` annotations.
4. Check for usage in imported components and remove the term from any tsvs used for axiom generation (see below). Axioms can be pulled into the active ontology (editors' file) by right clicking in Protege if they need to be kept (see step 5).
5. Remove all logical axioms and retain only label, id, namespace, definition, comment, synonym, contributor, date, replaced_by and consider annotation axioms.
6. Add a `http://www.w3.org/2002/07/owl#deprecated` annotation with the boolean value `true`.

Edits to related terms:

1. Add the obsoleted term label (without `obsolete`) and synonyms to replacement term(s) if appropriate.
2. Copy definition information and references to replacement term(s) if appropriate.
3. Check for (and modify) usage of the obsolete term by other terms (`Usage` tab in Protege).

## Design Patterns

Design patterns can be used to maintain and generate complete terms (labels, definitions, synonyms etc) or to generate a subset of the logical/annotation axioms, with other axioms being maintained in the editors' file. When creating new terms, consider whether they might fit an existing design pattern before manually adding axioms to the editors' file.

See DOSDP [paper](https://jbiomedsem.biomedcentral.com/articles/10.1186/s13326-017-0126-0) and [GitHub](https://github.com/INCATools/dead_simple_owl_design_patterns).

DOSDP design pattern yaml files are found in [../patterns/dosdp-patterns](../patterns/dosdp-patterns). Fillers are in tsv files in [../patterns/data/all-axioms](../patterns/data/all-axioms) for generation of logical and annotation axioms, or [../patterns/data/logical-only](../patterns/data/logical-only) for generation of only logical axioms. Any (yaml and tsv) pair of files that share a name (apart from the extension) are assumed to be a DOSDP design pattern and a corresponding tsv specifying axioms to add.

After updating term IDs in a filler tsv, labels can be automatically updated by running `sh run.sh make update_pattern_labels` to aid human readability/checking.

To compile design patterns, run `sh run.sh make patterns`. This generates a file [../patterns/definitions.owl](../patterns/definitions.owl), which is imported by the editor's file.

Design pattern tests are skipped, as the ALNeuronEquivalentClass pattern fails, but actual design pattern compilation should succeed when run.

## Robot Templates

When adding a large number of similar terms from the same data source, it is sometimes best to use a custom [robot template](https://robot.obolibrary.org/template). Some term files generated from templates can be merged into the editors' file. Other files, especially those describing more provisional cell types, are maintained as components (in [components](components)), so that they can be more easily updated. Components that are generated from robot templates are:

- `flywire_neurons.owl`
- `hemibrain_new_ALLNs.owl`
- `hemibrain_new_cells.owl`
- `manc_new_cells.owl`
- `optic_lobe_neurons.owl`
- `VNC_new_cells.owl`

Source data and notebooks for generating templates can be found in [../patterns/robot_template_projects](../patterns/robot_template_projects).

## Neuron Symbols

Many neurons have a single, unique short identifier as a symbol (IAO:0000028) annotation (similar to gene symbols). These are maintained in the [neuron_symbols.tsv](neuron_symbols.tsv) file, which is used to generate [components/neuron_symbols.owl](components/neuron_symbols.owl). When adding/modifying symbols it is important to check that both the term ID and symbol are unique within the file. Adding a reference publication is optional, but recommended. Symbols should not be maintained as synonyms in the editors' file (or elsewhere), as they will be automatically generated as typed (`official symbol used on Virtual Fly Brain`) synonyms in the symbols component.

## SSSOM Mappings

Mappings to external resources are maintained in [../mappings](../mappings). These are merged and used to produce [components/mappings_xrefs.owl](components/mappings_xrefs.owl) as well as being released as a separate tsv [../../fbbt.sssom.tsv](../../fbbt.sssom.tsv). New mapping files must be added to `MAPPING_SETS` in [fbbt.Makefile](fbbt.Makefile).

See SSSOM [paper](https://academic.oup.com/database/article/doi/10.1093/database/baac035/6591806) and [GitHub](https://github.com/mapping-commons/sssom).

## Extended Logical Axioms

The [components/fbbt_ext.owl](components/fbbt_ext.owl) file contains axioms that are awkward to represent in obo format. Most of these appear in the `General class axioms` section when viewing the editors' file in Protege, under the `Active ontology` tab. To add a new axiom, create it in this location in Protege, then right click to `Move axiom(s) to ontology...` and select `fbbt_ext`.

## Other Components
Two components are automatically updated during the release process and do not require any manual edits:

- The [components/flybase_import.owl](components/flybase_import.owl) file contains annotation from FlyBase for genes used in FBbt axioms.
- The [components/VFB_xrefs.owl](components/VFB_xrefs.owl) file contains axioms that are used to generate linkouts to Virtual Fly Brain from the FlyBase website for nervous system terms.

The `qc_assertions` files were historically used to allow some qc checks to pass, but might no longer be needed.

## Imports

All import modules are in the [imports](imports) folder.

To include new classes in an import module:

1. Reference an external ontology class in the editors' file. In Protege: add as a new class directly under owl:Thing and paste in the PURL, then add a relationship to the new term from an FBbt term.
2. Run: `sh run.sh make all_imports` to regenerate imports.

To add a new import module:

1. Add the short form of the ontology you wish to import to the list of imports in [fbbt-odk.yaml](fbbt-odk.yaml).
2. Run: `sh run.sh update_repo`
3. Add lines to [catalog-v001.xml](catalog-v001.xml) and add a new Import statement to the editors' file for the newly-imported ontology.
4. Add a class from the ontology you wish to import as above.


## Travis Continuous Integration System

Travis checks must be run (and passed) on all PRs before merging.

Check the build status here: [![Build Status](https://api.travis-ci.com/FlyBase/drosophila-anatomy-developmental-ontology.svg?branch=master&status=created)](https://app.travis-ci.com/github/FlyBase/drosophila-anatomy-developmental-ontology)

The way QC now works for all four FB ontologies is this:

  1. We run the whole (slightly modified) pipeline (encoded in [travis.sh](travis.sh))
  2. In the end some hard QC is run. This QC can be controlled through the file [qc-profile.txt](qc-profile.txt).

# Releases

FlyBase ontologies are usually released over the course of a day or two, in the order:
1. FBdv
2. FBbt
3. DPO
4. FBcv

This order is important because DPO imports FBdv and FBbt, and FBcv imports DPO.

You should only attempt to make a release if the travis build is passing on the master branch.

These instructions assume you have [docker](https://www.docker.com/get-docker) running. The script [run.sh](run.sh) wraps docker commands.

Everything should be done from this (`src/ontology`) folder.

## Release Procedure

1. Make a branch (directly from master) for the release.

2. Run `sh run_release.sh`
 * This generates derived files such as `fbbt.owl` and `fbbt.obo` and places them in the top level (`../..`).
 * Imports, DOSDP axioms and some components will be automatically updated as part of the release process, so no additional steps need to be run.
 * Note that the versionIRI value will be automatically added, and will end with `YYYY-MM-DD`, as per OBO guidelines.

3. Checks:
 * Check the diff (header and Typedefs of `fbbt.obo` are usually most informative).
 * Check reports (in [reports](reports) folder), particularly `chado_load_check_simple.txt` and `obo_qc_fbbt.obo.txt`.
 * Look at the diff for the `spellcheck.txt` report. Add any new words to the [dictionary](../../tools/dictionaries/standard.dict).

4. Make any necessary changes, then redo steps 2 & 3.

5. Commit and push the files and make a PR in the usual way.

6. When travis checks have passed, merge the PR and IMMEDIATELY make a new release on GitHub (see below).

## Releasing on GitHub

This can be done automatically or manually (see below).

__IMPORTANT__: The value of the "Tag version" field MUST be `vYYYY-MM-DD`
The initial lowercase "v" is REQUIRED. The YYYY-MM-DD *must* match what is in the `owl:versionIRI` of the derived fbbt.owl (`data-version` in fbbt.obo), which will be today's date. This cannot be changed after the fact, be sure to check that this is right, whether releasing manually or automatically.

__IMPORTANT__: NO MORE THAN ONE RELEASE PER ONTOLOGY PER DAY.

The PURLs are configured to pull from github. This means that BOTH ontology purls and versioned ontology purls will resolve to the correct ontologies.

 * http://purl.obolibrary.org/obo/fbbt.owl <-- current ontology PURL
 * http://purl.obolibrary.org/obo/fbbt/releases/2025-05-29/fbbt.owl <-- specific release
 
### Automated Release

This is the preferred method, to avoid errors.

To set this up, create a [GitHub token](https://github.com/settings/tokens/new) from your GitHub account and make sure it has the `repo` scope enabled. Store the token in a `~/Library/Application Support/ontology-development-kit/github/token` file.

After merging a new release on GitHub, run `sh run.sh make public_release` on the command line.

This will automatically create a draft release with the correct tag, title, release notes, and attached release assets. Check that the draft is OK, edit the release notes if desired, then publish the release.

### Manual Release

Go to:
https://github.com/FlyBase/drosophila-anatomy-developmental-ontology/releases/new

Create an appropriate tag (see above) and title. The title should be `YYYY-MM-DD`, optionally followed by a description (e.g. `January release`).

Attach all the release artefacts (located in the top-level directory) to the release as release "assets".

You can also add release notes in markdown format (this can be done after publishing).

Then click `Publish release`.
