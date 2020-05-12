
from  uk.ac.ebi.vfb.neo4j.flybase2neo.feature_tools import FeatureMover
import pandas as pd
from collections import OrderedDict

fm = FeatureMover('http://pdb.virtualflybrain.org', 'neo4j', 'neo4j')  # expects some neo connection, not used here

# create list of FBgns from seed.txt

with open('../../../ontology/seed.txt', 'r') as f:
    terms = f.readlines()

FBgn_list = [str(term.rstrip()).lstrip('http://flybase.org/reports/') for term in terms if "FBgn" in term]

"""
# Make template from a file of FBgns
with open('FBgns.txt', 'r') as f:
    FBgns = f.readlines()

FBgn_list = [gene.rstrip() for gene in FBgns]
"""

# Get dictionary of Nodes for list of FBgns
fb_output = fm.name_synonym_lookup(FBgn_list)

# Make a dictionary with key - column header & value = template specification (first row of table).
template_seed = OrderedDict([ ('ID' , 'ID'), ('CLASS_TYPE' , 'CLASS_TYPE'),
                              ('RDF_Type' , 'TYPE' ), ("Label" , "A rdfs:label"),
                              ("Synonyms" , "A oboInOwl:hasExactSynonym SPLIT=|"),
                              ("Subclass_of" , "SC %")])

# Create dataFrame for template
template = pd.DataFrame.from_records([template_seed])

for g in FBgn_list:

    row_od = OrderedDict([]) #new template row as an empty ordered dictionary
    for c in template.columns: #make columns and blank data for new template row
        row_od.update([(c , "")])

    # gets Node (class) for gene
    gene = fb_output[g]

    #these are the same in each row
    row_od["CLASS_TYPE"] = "subclass"
    row_od["RDF_Type"] = "owl:Class"
    row_od["Subclass_of"] = "http://purl.obolibrary.org/obo/SO_0000704"

    #ID, label
    row_od["ID"] = gene.iri
    row_od["Label"] = gene.label

    #synonyms
    syn_string = ""
    for syn in gene.synonyms:
        syn_string += (syn + "|")
    syn_string = syn_string.rstrip("|")
    row_od["Synonyms"] = syn_string

    #make new row into a DataFrame and add it to template
    new_row = pd.DataFrame.from_records([row_od])
    template = pd.concat([template, new_row], ignore_index=True, sort=False)

template.to_csv("./template.tsv", sep = "\t", header=True, index=False)
