#!/usr/bin/env perl

use warnings;
require OboModel;
use strict;

my ($obo_stag, $obo_mtag, $obo_stanza, $relations, $obo_header) = OboModel::obo_parse($ARGV[0]);

while (my ($id, $tag) = each %$obo_stag) {
  if ($tag->{def} =~ m/\$sub_(\w+\:\d+)/) {
    my $sub_term_id = $1;
    if (exists $obo_stag->{$sub_term_id}->{def}) {
      $tag->{def} =~ s/\$sub_(\w+\:\d+)/$obo_stag->{$sub_term_id}->{def}/;
      $tag->{def_dbxref} = "$tag->{def_dbxref}, $obo_stag->{$sub_term_id}->{def_dbxref}"
    } else {
      warn "No def for $sub_term_id in source file"
    }
  }
}

OboModel::obo_print($obo_stag, $obo_mtag, $obo_stanza, $relations, $obo_header);



