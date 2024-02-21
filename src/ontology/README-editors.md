These notes are for the EDITORS of FBbt

This project uses the [ontology development kit](https://github.com/INCATools/ontology-development-kit).

For more details on ontology management, please see the [OBO tutorial](https://github.com/jamesaoverton/obo-tutorial) or the [Gene Ontology Editors Tutorial](https://go-protege-tutorial.readthedocs.io/en/latest/).

You may also want to read the [GO ontology editors guide](http://go-ontology.readthedocs.org/).

## Requirements

 1. [Protege](https://protege.stanford.edu/) (for editing)
 2. A git client (we assume command line git)
 3. [docker](https://www.docker.com/get-docker) (for managing releases)

## Editing the Ontology

First, clone the repository:

`git clone https://github.com/FlyBase/drosophila-anatomy-developmental-ontology.git`

Make sure you have an ID range in the [idranges file](fbbt-idranges.owl) (see below).

The editors' version is [fbbt-edit.obo](fbbt-edit.obo), [../../fbbt.owl](../../fbbt.owl) is the release version.

** DO NOT EDIT fbbt.obo OR fbbt.owl in the top level directory **

Changes to the editors' file should be made on a branch and merged via a Pull Request (PR) after travis checks have passed. If your changes relate to an issue, link the PR to the issue using 'related to #' or 'fixes #' as appropriate in the PR description.

## ID Ranges

These are stored in the file [fbbt-idranges.owl](fbbt-idranges.owl)

** ONLY USE IDs WITHIN YOUR RANGE!! **

If you do not have an ID range, get one from the maintainer of this repo.

Note: Protege does not read the file, it is up to you to ensure correct Protege configuration (under Protege > Preferences > New entities) - see [ODK documentation](https://ontology-development-kit.readthedocs.io/en/latest/InitialSetup.html#setting-id-ranges-in-protege).

## Imports

All import modules are in the [imports/](imports/) folder.

To include new classes in an import module:

1. Reference an external ontology class in the edit ontology. In Protege: add as a new class directly under owl:Thing and paste in the PURL, then add a relationship to the new term from an fbbt term.
2. Run: `sh run.sh make all_imports` to regenerate imports.

To add a new import module:

1. Add the short form of the ontology you wish to import to the list of imports in [fbbt-odk.yaml](fbbt-odk.yaml).
2. Run: `sh run.sh make update_repo`
3. Add lines to [catalog-v001.xml](catalog-v001.xml) and add a new Import statement to the editors' file for the newly-imported ontology.
4. Add a class from the ontology you wish to import as above.

## Design Patterns

You can automate (class) term generation from design patterns by placing DOSDP yaml files in src/patterns/dosdp-patterns and tsv files in src/patterns/data/default. Any pair of files that share a name (apart from the extension) are assumed to be a DOSDP design pattern and a corresponding tsv specifying terms to add.

Design patterns can be used to maintain and generate complete terms (names, definitions, synonyms etc) or to generate logical axioms only, with other axioms being maintained in editors' file.  This can be specified on a per-term basis in the TSV file.

Design pattern docs are checked for validity via Travis, but can be tested locally using

`sh run.sh make patterns`

In addition to running standard tests, this command generates an owl file (`src/patterns/pattern.owl`), which demonstrates the relationships between design patterns.

(At the time of writing, the following import statements need to be added to `src/patterns/pattern.owl` for all imports generated in `src/imports/*_import.owl`.   This will be automated in a future release.')

To compile design patterns to terms run:

`sh run.sh make ../patterns/definitions.owl`

This generates a file (`src/patterns/definitions.owl`).  You then need to add an import statement to the editor's file to import the definitions file.

## Releases

FlyBase ontologies are usually released over the course of a day or two, in the order:
1. FBdv
2. FBbt
3. DPO
4. FBcv

This order is important because DPO imports FBdv and FBbt, and FBcv imports DPO.

You should only attempt to make a release if the travis build is passing on the master branch.

These instructions assume you have [docker](https://www.docker.com/get-docker) running. The script [run.sh](run.sh) wraps docker commands.

Everything should be done from this (/src/ontology/) folder.

To release:

1. Make a branch (directly from master) for the release.

2. Run `sh run_release.sh`
 * This generates derived files such as fbbt.owl and fbbt.obo and places them in the top level (../..).
 * Note that the versionIRI value will be automatically added, and will end with YYYY-MM-DD, as per OBO guidelines.

3. Checks:
 * Check the diff (header and Typedefs of fbbt-simple.obo are usually most informative).
 * Check reports (in [reports/](reports/) folder)
 * Spell check using OBO-Edit

4. Make any necessary changes to the editors' file, then redo steps 2 & 3.

5. Commit and push the files and make a PR in the usual way.

6. When travis checks have passed, merge the PR and IMMEDIATELY make a new release on GitHub:

 * https://github.com/FlyBase/drosophila-anatomy-developmental-ontology/releases/new

__IMPORTANT__: The value of the "Tag version" field MUST be `vYYYY-MM-DD`

The initial lowercase "v" is REQUIRED. The YYYY-MM-DD *must* match what is in the `owl:versionIRI` of the derived fbbt.owl (`data-version` in fbbt.obo), which will be today's date. This cannot be changed after the fact, be sure to get this right!

Release title should be YYYY-MM-DD, optionally followed by a title (e.g. "January release")

Attach all the release artefacts (located in the top-level directory) to the release as release "assets".

You can also add release notes (this can also be done after the fact). These are in markdown format. In future we will have better tools for auto-generating release notes.

Then click "Publish release".

__IMPORTANT__: NO MORE THAN ONE RELEASE PER ONTOLOGY PER DAY.

The PURLs are already configured to pull from github. This means that BOTH ontology purls and versioned ontology purls will resolve to the correct ontologies. Try it!

 * http://purl.obolibrary.org/obo/fbbt.owl <-- current ontology PURL
 * http://purl.obolibrary.org/obo/fbbt/releases/2021-03-11/fbbt.owl <-- specific release

For questions on this contact Chris Mungall or email obo-admin AT obofoundry.org

## Automating release creation

The last step above (6, making a release on GitHub) can be done almost entirely automatically. For that, create a [GitHub token](https://github.com/settings/tokens/new) from your GitHub account and make sure it has the `repo` scope enabled. Store the token in a `~/Library/Application Support/ontology-development-kit/github/token` file.

Then, to make a release, after having merged the PR in step 5 above, run `sh run.sh make public_release`.

The command will automatically create a draft release with the correct tag, title, release notes, and attached release assets. Check that the draft is OK, edit the release notes if desired, then publish the release.

# Configurable Options:

- src/ontology/blacklisted_classes.txt contains a set of classes that are removed from the ontology no matter what. This can be useful when imports import classes you do not care about.

# Travis Continuous Integration System

Check the build status here: [![Build Status](https://travis-ci.com/FlyBase/drosophila-anatomy-developmental-ontology.svg?branch=master)](https://travis-ci.com/FlyBase/drosophila-anatomy-developmental-ontology)

The way QC now works for all four ontologies is this:

  1. We run the whole (slightly modified) pipeline (encoded in [travis.sh](travis.sh))
  2. In the end some hard QC is run. This QC can be controlled through the file [qc-profile.txt](qc-profile.txt). It is pretty permissive now, because there are some errors.

# Updates

To get the latest version of ODK, run: `docker pull obolibrary/odkfull`

To update the repo (Makefile etc.), run: `sh run.sh make update_repo`

# Makefile notes

NEVER edit the [Makefile](Makefile) - this file is managed by the ODK and will be replaced when repo is upgraded.

For changing the the pipeline, edit [fbbt.Makefile](fbbt.Makefile) - everything added here will override instructions in the other Makefile.
