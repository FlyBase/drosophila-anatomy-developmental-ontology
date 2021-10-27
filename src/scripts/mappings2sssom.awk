BEGIN {
	FS = "\t";
	print "#curie_map:";
	print "#  FBbt: \"http://purl.obolibrary.org/obo/FBbt_\"";
	print "#  UBERON: \"http://purl.obolibrary.org/obo/UBERON_\"";
	print "#  CL: \"http://purl.obolibrary.org/obo/CL_\"";
	print "#  skos: \"http://www.w3.org/2004/02/skos/core\"";
	print "#mapping_provider: \"http://purl.obolibrary.org/obo/FBbt.owl\"";
	print "subject_id\tsubject_label\tpredicate_id\tobject_id\tmatch_type";
}

/^#/ { next }
/^$/ { next }

{
	if ( $3 == "exact" ) {
		predicate = "skos:exactMatch"
	}
	else {
		predicate = "skos:relatedMatch"
	}
	print $1"\t"$4"\t"predicate"\t"$2"\tHumanCurated";
}
