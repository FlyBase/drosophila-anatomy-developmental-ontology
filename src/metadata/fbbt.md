---
layout: ontology_detail
id: fbbt
title: Drosophila Anatomy Ontology
jobs:
  - id: https://travis-ci.org/FlyBase/drosophila-anatomy-ontology
    type: travis-ci
build:
  checkout: git clone https://github.com/FlyBase/drosophila-anatomy-ontology.git
  system: git
  path: "."
contact:
  email: 
  label: 
  github: 
description: Drosophila Anatomy Ontology is an ontology...
domain: stuff
homepage: https://github.com/FlyBase/drosophila-anatomy-ontology
products:
  - id: fbbt.owl
    name: "Drosophila Anatomy Ontology main release in OWL format"
  - id: fbbt.obo
    name: "Drosophila Anatomy Ontology additional release in OBO format"
  - id: fbbt.json
    name: "Drosophila Anatomy Ontology additional release in OBOJSon format"
  - id: fbbt/fbbt-base.owl
    name: "Drosophila Anatomy Ontology main release in OWL format"
  - id: fbbt/fbbt-base.obo
    name: "Drosophila Anatomy Ontology additional release in OBO format"
  - id: fbbt/fbbt-base.json
    name: "Drosophila Anatomy Ontology additional release in OBOJSon format"
dependencies:
- id: go
- id: ro
- id: pato

tracker: https://github.com/FlyBase/drosophila-anatomy-ontology/issues
license:
  url: http://creativecommons.org/licenses/by/3.0/
  label: CC-BY
activity_status: active
---

Enter a detailed description of your ontology here. You can use arbitrary markdown and HTML.
You can also embed images too.

