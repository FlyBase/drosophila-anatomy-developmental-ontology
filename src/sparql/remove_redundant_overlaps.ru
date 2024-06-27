PREFIX overlaps: <http://purl.obolibrary.org/obo/RO_0002131>
PREFIX part_of: <http://purl.obolibrary.org/obo/BFO_0000050>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

DELETE {
  ?sub rdfs:subClassOf ?a
}

WHERE {
  ?sub rdfs:subClassOf ?a .
  ?sub rdfs:subClassOf ?b .
  ?a rdf:type owl:Restriction .
  ?a owl:onProperty overlaps: .
  ?a owl:someValuesFrom ?obj .
  ?b rdf:type owl:Restriction .
  ?b owl:onProperty part_of: .
  ?b owl:someValuesFrom ?obj .
}