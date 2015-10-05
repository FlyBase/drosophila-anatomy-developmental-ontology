#!/usr/bin/perl -w
require Gen_EC_def;
require OboModel;
use strict;

my ($obo_stag, $obo_mtag, $obo_stanza, $relations, $obo_header) = OboModel::obo_parse($ARGV[0]);

my $new_def = Gen_EC_def::get_EC_def($obo_mtag, $obo_stag);

my ($id, $stanza) = '';
print "$$obo_header\n\n";
while (($id, $stanza) = each %$obo_stanza) {
  if (exists ($new_def->{$id})) {
    if (!($stanza =~ m/def\: "..+"/)) {
      if ($stanza =~ m/def\: "\." \[.*\]\n/) {
	$stanza =~ s/def\: "\." \[.*\]\n/$new_def->{$id}\n/ 
      } else {
	$stanza .= "\n".$new_def->{$id}
      }
    }
  }
  print "\[Term\]\n$stanza\n\n";
}
print "\[Typedef\]\n$_\n\n", foreach (@{$relations});

