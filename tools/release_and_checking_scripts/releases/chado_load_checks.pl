#!/usr/bin/env perl
use warnings;
require OboModel;
use strict;
use Business::ISBN; 

=use chado_load_checks.pl <file to check>

This script runs the following checks:

1. Are there multiple terms with the same name?

2. Do all non-anonymous terms have names?

3. Are def_dbxrefs and synonym_dbxrefs one of the following:

FlyBase:FBrfnnnnnnn; 
FlyBase:FBimnnnnnnn;
FBC:\<curator initials\>;
PMID:\d+; 
http://...;
ISBN:<legal ISBN13>;
CARO:<CARO curator initials>.

Note - this is the allowable list for FBbt and FBdv.  FBcv terms that import def_dbxrefs from GO may have dbxrefs from the longer, GO approved list: https://flybase.org/svn/ontologies/CVS_versions/GO.xrf_abbs.  There are currently no scripted checks of this list.

2. Checks for descriptions inserted into synonym or def dbxref lists:
It is legal in OBO 1.2 format for synonym  or def dbxref lists to include quoted descriptions of references following each dbxref. Depending on the setup of the OboEdit reference library, these may be inserted automatically when adding references. However,  GO::Parser (used in loading) fails to strip out these comments before parsing as a comma delimited list, leading badly formatted xrefs and failure of loading into chado.

3. Checks (via OboModel STDERR) that all Term stanza tags are from the following allowable list:
/^name\: |^id\: |^namespace\: |^def\: |^comment\: |^intersection_of\: |^relationship\: |^xref\: |^synonym\: |^is_a\: |^subset\: |^union_of\: |^is_obsolete\: |^is_anonymous\: |^disjoint_from\: |^alt_id\: |^consider\: |^replaced_by\: |^creation_date\: |^created_by\: |^exact_synonym\: |^broad_synonym\: |^narrow_synonym\: |^related_synonym\: |^xref_analog\:/

4. Checks that namespaces match id-prefixes.

=cut

# TODO: 
# Extend to deal with relations


my ($obo_stag, $obo_mtag, $obo_stanza, $relations, $obo_header) = OboModel::obo_parse($ARGV[0]);

&chado_load_checks ($obo_stag, $obo_mtag);

sub chado_load_checks {
  my $obo_stag = $_[0];
  my $obo_mtag = $_[1];

  my $fail_stat = 0;
  my ($key, $value);
  my %name_id;
  my %alt_id;
  while (($key, $value) = each %$obo_mtag) {
    for (@{$value}) {
      if ($_->{obj}) {
	my $obj = ($_->{obj});
	if ($_->{estat} eq 'alt_id') {
	  $alt_id{$_->{obj}} = 1
	} elsif ($obo_stag->{$obj}->{is_obsolete}) {  
	  $fail_stat = 1;
	  print "$key ; $obo_stag->{$key}->{name} has relationship to an obsolete term, $obj ; $obo_stag->{$obj}->{name}\n";
	}
      }
    }
  }
  while (($key, $value) = each %$obo_stag) {
    if ($key =~ m/FBbt\:|FBdv\:|FBcv\:/) { # limit checks to FBbt, FBdv, FBcv stanzas
      if (exists($alt_id{$key})) {
	 print "$key is both a primary and secondary ID\n";
	 $fail_stat = 1;
       }
      if ((!$value->{name})&&(!$value->{is_anonymous})) {  # Do all non-anonymous terms have names?
	$fail_stat = 1;	  
	print "$key does not have anonymous term status but has no name\!\n";
      }
      my $name = $value->{name}; # Are there multiple terms with the same name?
      unless (exists $name_id{$name}) {
	$name_id{$name}=$key;
      } else {
	$fail_stat = 1;
	print "The name \'$name\' is shared by $key and $name_id{$name}.\n";
      }
      print "$key \! ".$value->{name}." has description inserted in its def_db_xref list\n", if ($value->{def_dbxref_dstat}); # check for quotes in def_dbxrefs
 # namespace checks
      $key =~ m/(\w+)\:\d+/;
      my $idp = $1;
      if ($idp eq 'FBbt') {
	unless ($value->{namespace} eq 'fly_anatomy.ontology') {
	  $fail_stat = 1;
	  print "$value->{namespace} is not a valid namespace for $key.\n"
	}
      }
      elsif ($idp eq 'FBdv') {
	unless ($value->{namespace} eq 'FlyBase_development_CV') {
	  $fail_stat = 1;
	  print "$value->{namespace} is not a valid namespace for $key.\n"
	}
      }
      elsif ($idp eq 'FBcv') {
	unless ($value->{namespace} =~ m/FlyBase miscellaneous CV$|^allele_class$|^biological_process$|^clone_qualifier$|^disease_qualifier$|^dominance_qualifier$|^embryonic_pattern_qualifier$|^environmental_qualifier$|^expression_qualifier$|^extent$|^fly_anatomy.ontology$|^genetic_interaction_type$|^genotype_to_phenotype_relation$|^group_descriptor$|^homeotic$|^intensity_qualifier$|^language$|^mode_of_assay$|^origin_of_mutation$|^phenotypic_class$|^pub_type$|^quality$|^scorability$|^sex_qualifier$|^spatial_qualifier$|^structural_qualifier$|^temporal_qualifier$|^precursor_qualifier$|^progressive_qualifier$|^assay_attribute$|^assay_type$|^biosample_attribute$|^biosample_type$|^dataset_entity_type$|^project_attribute$|^project_type$|^reagent_collection_type$|^result_attribute$|^result_type$|^experimental_tool_descriptor$/) { 
	  $fail_stat = 1;
	  print "$value->{namespace} is not a valid namespace for $key.\n"
	}
      } else {
	print STDERR "I don't know what namespaces are valid for $idp.\n"
      }
      my @def_dbxrefs = split /, /, $value->{def_dbxref};
      for (@def_dbxrefs) {
	print "$key \! $value->{name} has unnapproved def_dbxref type: $_\n",  unless (is_dbxref_legal($_))
      }
      for (@{$obo_mtag->{$key}}) {
	if ($_->{estat} eq 'xref') {
	  print "$key \! $value->{name} has unnapproved xref type: $_->{an}\n", unless ($_->{an} =~ m/\w+\:.+/)
	}
	if (($_->{estat} eq 'syn')&&($_->{axref})) {
	  my @syn_dbxrefs = split /, /, $_->{axref};
	  for (@syn_dbxrefs) {
	    print " $key \! $value->{name} has unnapproved syn_dbxref type: $_\n",  unless (is_dbxref_legal($_))
	  }
	}
      }
    }
  }
die 'Please see output for script failure reasons', if  ($fail_stat);

}


sub is_dbxref_legal {
  my $xref = $_[0];
  my $legal_stat=1;
  if ($xref =~ m/ISBN\:(.+)/) { # Is xref a valid ISBN13 ?
    &ISBN13_check($1)
  }
  # If not ISBN, does it follow one of the other legal dbxref syntaxes?
  elsif ($_ =~ m/FlyBase\:FBrf\d{7}|VFB_vol\:\d{8}|FBC\:\S+|SO\:ma|FlyBase\:FBim\d{7}|PMID\:\d+|http\:\/\/.+|CARO\:\S+|doi\:\d+\.\d+\/\w+|FlyBrain_NDB\:\d+|CHEBI\:\d+|MeSH\:D\d+|GOC:\S+|GO_REF\:\d+|Reactome\:\d+|SO\:\S+|UniProt\:P\d+|UniProt\:Q\S+|WB_REF\:\S+|FB\:FBrfd{7}|Wikipedia\:\S+/) {
    $legal_stat=1;
  } else {
    $legal_stat=0
  }
  return $legal_stat;
}


sub ISBN13_check { 
  # Checking ISBN validity
  my $isbn_2_test = $_[0];
  my $isbn = Business::ISBN->new($isbn_2_test);
  if ($isbn) {
    print "ISBN\:$isbn_2_test is not a valid ISBN.\n", unless (my $isbn_stat = $isbn->is_valid)
  } else {
    print "ISBN\:$isbn_2_test is not a valid ISBN\n";
    return
  }
  my $isbn13 = $isbn->as_isbn13;
   unless ($isbn->as_string eq $isbn13->as_string) {
     print "Please change ISBN\:$isbn_2_test to ISBN\:".$isbn13->as_string.", to conform to ISBN13 standard.\n";
     return
   }
  unless (($isbn_2_test eq $isbn->as_string)&&($isbn_2_test eq $isbn13->as_string)) {
    print "Hyphenation of ISBN\:$isbn_2_test is incorrect, please use ISBN:".$isbn13->as_string."\n";
    return
  }
}
  
