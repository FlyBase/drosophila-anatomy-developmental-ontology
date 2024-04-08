BEGIN {
	FS = "\t";
	print "#curie_map:";
	print "#  CL: \"http://purl.obolibrary.org/obo/CL_\"";
	print "#  FBbt: \"http://purl.obolibrary.org/obo/FBbt_\"";
	print "#  ORCID: \"https://orcid.org/\"";
	print "#  UBERON: \"http://purl.obolibrary.org/obo/UBERON_\"";
	print "#  obo: \"http://purl.obolibrary.org/obo/\"";
	print "#mapping_set_id: \"http://purl.obolibrary.org/obo/fbbt/fbbt-mappings.sssom.tsv\"";
	print "#mapping_set_description: \"Mappings between the Drosophila Anatomy Ontology and foreign ontologies.\"";
	print "#creator_id:";
	print "#  - \"ORCID:0000-0002-6095-8718\"";
	print "#license: \"https://creativecommons.org/licenses/by/4.0/\"";
	print "#subject_source: \"obo:fbbt.owl\"";
	print "#mapping_date: \""date"\"";
	print "subject_id\tsubject_label\tpredicate_id\tobject_id\tmapping_justification\tobject_source";
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
	if ( $2 ~ /^UBERON:/ ) {
		object_source = "obo:uberon.owl";
	} else if ( $2 ~ /^CL:/ ) {
		object_source = "obo:cl.owl";
	}
	print $1"\t"$4"\t"predicate"\t"$2"\tsemapv:ManualMappingCuration\t"object_source;
}
