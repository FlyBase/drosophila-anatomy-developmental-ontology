#!/usr/bin/python

import csv
from collections import OrderedDict

def csv2dict(filename):
    reader = csv.DictReader(open(filename, 'rb'))

    csvdict = OrderedDict()
    for row in reader:
        csvdict[row['id']] = row['label']

    return csvdict

GO_dict = csv2dict('GO_labels.csv')
fbbt_dict = csv2dict('fbbt_labels.csv')

fbbt_to_drop = [fbbt for fbbt,label in fbbt_dict.items() if label in GO_dict.values()]
fbbt_to_drop = [fbbt.replace('http://purl.obolibrary.org/obo/FBbt_','FBbt:') for fbbt in fbbt_to_drop]
fbbt_to_drop = sorted(fbbt_to_drop)

with open ('duplicate_terms.txt', 'w') as f:
    for item in fbbt_to_drop:
        f.write("%s\n" % item)
