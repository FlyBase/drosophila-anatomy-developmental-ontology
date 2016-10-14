#!/usr/bin/perl -w
package Gen_EC_def;
use strict;

our (@ISA, @EXPORT, $VERSION);

use Exporter;
$VERSION= 1.00;
@ISA = qw(Exporter);
@EXPORT= qw (&get_EC_def);
1;

#########################

sub get_EC_def {
  my %new_defs;
  my $obo_mtag = $_[0];
  my $obo_stag = $_[1];
#  my ($id, $value) = '';
#  while (($id, $value) = each %$obo_stag) {
  foreach my $id (keys %{$obo_stag}) {

    my $new_def = '';
    my $genus = '';
    my @diff = ();

    foreach (@{$obo_mtag->{$id}}) {
      if (($_->{estat} eq 'equivalent_to')&&(exists $obo_stag->{$_->{obj}}->{def}) &&  $obo_stag->{$_->{obj}}->{def}) {
# using lcfirst function to make first letter of the CHEBI imported definition lowercase
	$new_def = "def\: \"Mutation induced by exposure to " . lcfirst $obo_stag->{$_->{obj}}->{def} . " \(Definition imported and edited from \'$obo_stag->{$_->{obj}}->{name} \; $_->{obj}\', which is related to this term\.\)";
      }
      elsif ($_->{estat} eq 'int') {
	if ($_->{rel} eq 'is_a') {
	  my $genus_id = $_->{obj};
	  my $genus_name = $obo_stag->{$genus_id}->{name};
	  $genus = "Any $genus_name \($genus_id\)"
	}
	if (($_->{estat} eq 'int')&&(!($_->{rel} eq 'is_a'))) {
	  my $rel_string = &relation_2_englishish($_->{rel});
	  my $diff_id = $_->{obj};
	  my $diff_name = $obo_stag->{$diff_id}->{name};
	  my $diff = " that $rel_string ".$diff_name." \(".$diff_id."\)";
	  push @diff, $diff;
	}
      }
    }
    if (@diff) {
      $new_def = "def\: \"".$genus;
      $new_def .= pop (@diff);
      foreach (@diff) { 
	$new_def .= " and$_";
      }
    }
    if ($new_def) {
      my $new_def_dbxref = "FBC:auto_generated_definition";
      $new_def_dbxref .= ", ".$obo_stag->{$id}->{def_dbxref}, if ($obo_stag->{$id}->{def_dbxref});
      $new_def .= "\.\" \[".$new_def_dbxref."\]";
      $new_defs{$id}=$new_def;
    }
  }
  return (\%new_defs)
}

sub relation_2_englishish {
  my $relation = $_[0];
  my $out = '';
  $out = 'functions in (some)', if ($relation eq 'has_function_in');
  $out = 'has a dendrite that innervates some', if ($relation eq 'dendrite_innervates');
  $out = 'has an axon that innervates some', if ($relation eq 'axon_innervates');
  $out = 'innervates some', if ($relation eq 'innervates');
  $out = 'is part of some', if ($relation eq 'part_of');
  $out = 'electrically synapses to', if ($relation eq 'electrically_synapsed_to');
  $out = "develops from some", if ($relation eq 'develops_from');
  $out = "develops directly from some", if ($relation eq 'develops_directly_from');
  $out = "is connected to some ", if ($relation eq  'connected to');
  $out = "fasciculates with some", if ($relation eq 'fasciculates_with');
  $out = "releases as a neurotransmitter, some", if ($relation eq 'releases_neurotransmitter');
  if (!$out) {
    $relation =~ s/\_/ /g;
    $out = "$relation some";
  }
  return $out;
}
