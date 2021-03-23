"""
Script to get label and synonym info for FlyBase genes from VFB and make a robot template.
Template can be used to generate a new flybase_import.owl file.
"""

import psycopg2
import pandas as pd
from collections import OrderedDict

# create list of FBgns from seed.txt
with open('../../../ontology/seed.txt', 'r') as f:
    terms = f.readlines()

FBgn_list = [str(term.rstrip()).lstrip('http://flybase.org/reports/') for term in terms if "FBgn" in term]

fb_con = psycopg2.connect(dbname='flybase',
                          host='chado.flybase.org',
                          user='flybase')
query = ("SELECT f.uniquename as fbid, s.name as ascii_name, "
         "stype.name AS stype, "
         "fs.is_current, s.synonym_sgml as unicode_name "
         "FROM feature f "
         "LEFT OUTER JOIN feature_synonym fs on (f.feature_id=fs.feature_id) "
         "JOIN synonym s on (fs.synonym_id=s.synonym_id) "
         "JOIN cvterm stype on (s.type_id=stype.cvterm_id) "
         "WHERE f.uniquename IN ('%s') ORDER BY fbid" % "','".join(FBgn_list))
with fb_con:
    with fb_con.cursor() as curs:
        curs.execute(query)
        desc = curs.description
        output = curs.fetchall()
fb_con.close()

colnames = []
for column in desc:
    colnames.append(column[0])

FBgn_dataframe = pd.DataFrame.from_records(output, columns=colnames) \
    .drop_duplicates(ignore_index=True).drop('unicode_name', axis=1)

# Header of robot template
template_seed = OrderedDict([('ID', 'ID'), ("Label", "A rdfs:label"),
                             ("Synonyms", "A oboInOwl:hasExactSynonym SPLIT=|"),
                             ("Subclass_of", "SC %")])

# Create DataFrame for template
template = pd.DataFrame.from_records([template_seed])

# add a row for each gene to the template
for gene in FBgn_list:

    row_od = OrderedDict([])  # new template row as an empty ordered dictionary
    for c in template.columns:  # make columns and blank data for new template row
        row_od.update([(c, "")])

    # subclass of SO:gene
    row_od["Subclass_of"] = "http://purl.obolibrary.org/obo/SO_0000704"

    # ID = full iri for FBgn
    row_od["ID"] = "http://flybase.org/reports/" + gene

    longname = list(set([l for l in FBgn_dataframe.query(
        'fbid == @gene & is_current & stype == "fullname"')['ascii_name']]))
    symbol = list(set([l for l in FBgn_dataframe.query(
        'fbid == @gene & is_current & stype == "symbol"')['ascii_name']]))
    synonyms = list(set([l for l in FBgn_dataframe.query(
        'fbid == @gene')['ascii_name'] if l not in (longname + symbol)]))
    if len(longname) > 1:
        raise ValueError("Multiple current long names for %s" % gene)
    if len(symbol) > 1:
        raise ValueError("Multiple current symbols for %s" % gene)

    row_od["Label"] = symbol[0]
    row_od["Synonyms"] = '|'.join(synonyms+longname)

    # make new row into a DataFrame and add it to template
    new_row = pd.DataFrame.from_records([row_od])
    template = pd.concat([template, new_row], ignore_index=True, sort=False)

template.to_csv("./template.tsv", sep="\t", header=True, index=False)
