
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

DELETE { ?s rdfs:label ?remove }
WHERE {
  {
    SELECT ?s (STRBEFORE(GROUP_CONCAT(?dupLabel; separator="|"), "|") AS ?remove) WHERE {
      ?s rdfs:label ?label, ?dupLabel .
      FILTER (?label != ?dupLabel)
    }
    GROUP BY ?s
  }
}