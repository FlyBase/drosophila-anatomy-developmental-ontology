### Drosophila anatomy and development ontologies

[![FBbt Build Status](https://app.travis-ci.com/FlyBase/drosophila-anatomy-developmental-ontology.svg?branch=master)](https://app.travis-ci.com/FlyBase/drosophila-anatomy-developmental-ontology)

The Drosophila anatomy and development ontologies are query-able reference sources for information on Drosophila anatomy and developmental stages.  They also provide controlled vocabularies for use in annotation and classification of data related to Drosophila anatomy, such as gene expression, phenotype and images.  They were originally developed by [FlyBase](http://www.flybase.org), who continue to maintain them and have used them for over 200,000 annotations of phenotypes and expression.  A number of other projects use these ontologies for annotation and to drive their query systems, including [Virtual Fly Brain](http://www.virtualflybrain.org) (VFB), [FlyProt](http://www.flyprot.org/) and [RedFly](http://redfly.ccr.buffalo.edu).  Extensive use of synonyms means that, given a suitably sophisticated autocomplete, users can find relevant content by searching with almost any anatomical term they find in the literature.

These ontologies are developed in the web ontology language [OWL2](http://www.w3.org/TR/owl2-primer/).  Their extensive formalisation in OWL can be used to drive sophisticated query systems. This is well illustrated by the query system on [VFB](http://www.virtualflybrain.org).  Direct queries of anatomy on this site can be used to search for neurons by their innervation or fasciculation patterns (e.g. [this query](http://www.virtualflybrain.org/do/ont_bean_list.html?action=synaptic&id=FBbt:00007401) for neurons with synaptic terminals in the antennal lobe). Queries of annotations on VFB also use an OWL pre-query to find all relevant anatomy terms (e.g. [this query](http://www.virtualflybrain.org/do/gene_list.html?action=geneex&id=FBbt:00003748) finds annotations of expression in all parts of the medulla and in neurons that have some part in the medulla).  For more details please see references 1 and 2 below. For examples of OWL-DL queries of the ontologies, please see our [query guide](https://github.com/FlyBase/drosophila-anatomy-developmental-ontology/wiki/Query-guide).

These ontologies are freely available under a [CC BY 4.0](LICENSE) license. Please see our [download guide](https://github.com/mmc46/drosophila-anatomy-developmental-ontology/wiki/Download-guide) for details of the various available versions of these ontologies. Please see our [attributions](https://github.com/mmc46/drosophila-anatomy-developmental-ontology/wiki/Attribution)  page for details of how to acknowledge us for their use.

## Request changes

__Can't find the term you need? Notice an error?  We want your help!__

We encourage anybody who uses these ontologies, either directly or via the resources that use them, to help improve the them by requesting additions or changes. Simply make a new issue on our [tracker](https://github.com/FlyBase/drosophila-anatomy-developmental-ontology/issues) to request new terms or to report synonyms, references or problems with definitions or relationships.

## Publications

 1. _Costa M., Reeve S., Grumbling G., Osumi-Sutherland D._ (2013) The Drosophila anatomy ontology. [Journal of Biomedical Semantics __4__(32).](http://dx.doi.org/10.1186/2041-1480-4-32)
 1. _Osumi-Sutherland D., Reeve S., Mungall C., Ruttenberg A. Neuhaus F, Jefferis G.S.X.E, Armstrong J.D._ (2012) A strategy for building neuroanatomy ontologies. [Bioinformatics __28__(9): 1262-1269.](http://dx.doi.org/10.1093/bioinformatics/bts113)
 1. _Milyaev N., Osumi-Sutherland D., Reeve S., Burton N., Baldock R.A., Armstrong J.D._ (2012) The Virtual Fly Brain Browser and Query Interface. [Bioinformatics __28__(3): 411-415](http://dx.doi.org/10.1093/bioinformatics/btr677)
 1. _Grumbling G., Strelets V., The FlyBase Consortium_ (2006) FlyBase: anatomical data, images and queries [Nucleic Acids Res. __34__(Database issue): D484–D488](http://dx.doi.org/10.1093/nar/gkj068)

## Funding

Development of the Drosophila anatomy and development ontologies has been funded by:

  * A series of grants to FlyBase from the [National Human Genome Research Institute](http://www.genome.gov/) at the [U.S. National Institutes of Health](http://www.nih.gov/), the most recent of which is #U41 HG000739. 
  * An Isaac Newton Trust grant to Michael Ashburner to fund the work of David Osumi-Sutherland, awarded in 2007: Standardising the representation of Drosophila anatomy and development for databases.
  * [BBBSRC](https://bbsrc.ukri.org/):BB/G02233X/1, awarded in 2009 to J.Douglas Armstrong, Michael Ashburner and David Osumi-Sutherland: Structured and graphical queries for Drosophila neuroscience data.
  * An [Isaac Newton Trust](https://www.newtontrust.cam.ac.uk/) grant to Cahir O'Kane to fund the work of Marta Costa, awarded in 2012: Neuroinformatic identification of new types of neuron in the Drosophila brain. 
  * [Wellcome Trust](http://www.wellcome.ac.uk/): Virtual Fly Brain: a global informatics hub for Drosophila neurobiology (WT105023MA) 2014-2017;  Virtual Fly Brain (Grant ref: 208379/Z/17/Z) (October 2017 to September 2021)
