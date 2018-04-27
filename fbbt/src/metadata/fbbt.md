---
layout: ontology_detail
id: fbbt
title: Drosophila anatomy ontology test
jobs:
  - id: https://travis-ci.org/dosumis/drosophila-anatomy-ontology-test
    type: travis-ci
build:
  checkout: git clone https://github.com/dosumis/drosophila-anatomy-ontology-test.git
  system: git
  path: "."
contact:
  email: cjmungall@lbl.gov
  label: Chris Mungall
description: Drosophila anatomy ontology test is an ontology...
domain: stuff
homepage: https://github.com/dosumis/drosophila-anatomy-ontology-test
products:
  - id: fbbt.owl
  - id: fbbt.obo
dependencies:
 - id: go
 - id: pato
 - id: ro
tracker: https://github.com/dosumis/drosophila-anatomy-ontology-test/issues
license:
  url: http://creativecommons.org/licenses/by/3.0/
  label: CC-BY
---

Enter a detailed description of your ontology here
