BEGIN {
	FS = "\t";
	print "#curie_map:";
	print "#  FBbt: \"http://purl.obolibrary.org/obo/FBbt_\"";
	print "#  UBERON: \"http://purl.obolibrary.org/obo/UBERON_\"";
	print "#  CL: \"http://purl.obolibrary.org/obo/CL_\"";
	print "#mapping_provider: \"http://purl.obolibrary.org/obo/FBbt.owl\"";
	print "subject_id\tsubject_label\tpredicate_id\tobject_id\tmapping_justification";
}

/^#/ { next }
/^$/ { next }

{
	if ( $3 == "exact" ) {
		predicate = "semapv:crossSpeciesExactMatch";
	}
	else if ( $3 == "broad" ) {
		predicate = "semapv:crossSpeciesBroadMatch";
	}
	else {
		predicate = "semapv:crossSpeciesCloseMatch"
	}
	print $1"\t"$4"\t"predicate"\t"$2"\tsemapv:ManualMappingCuration";
}
