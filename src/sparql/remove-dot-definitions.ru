PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

DELETE {
	?term ?defprop ?definition .
	?ax ?prop ?val .
}
WHERE {
  {
		VALUES ?defprop { obo:IAO_0000115 }
    ?term a owl:Class .
		?term ?defprop ?definition .
		?term ?defprop ?definition2 .
  }
	FILTER (?definition != ?definition2)
	FILTER(STRSTARTS(STR(?term), "http://purl.obolibrary.org/obo/FBbt"))
	FILTER(STR(?definition) = "." || regex(STR(?definition), "\\$sub"))
	FILTER(isIRI(?term))
	
	# get any axiom annotations on those terms
	OPTIONAL { 
		?ax owl:annotatedSource ?term .
		?ax owl:annotatedTarget ?definition .
		?ax ?prop ?val .
		FILTER(isBlank(?ax)) 
	}
}