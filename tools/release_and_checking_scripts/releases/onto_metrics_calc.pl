#!/usr/bin/perl -w

require OboModel;
use strict;

my $namespace = $ARGV[0];
my ($obo_stag, $obo_mtag) = OboModel::obo_parse($ARGV[1]);

my $tot_count = 0 ;
my $def_count = 0 ;
my $EC_count = 0;
my ($id, $stag) = '';
while (($id, $stag) = each %$obo_stag) {
  my $EC_stat = 0; # For tracking whether term has an equivalent class def.
#  print "$id ; $stag->{name} ; $stag->{is_obsolete} \n";
  unless ($stag->{is_obsolete}) { # Ignore obsoletes
    if ($namespace) {
      next, unless ($stag->{namespace} eq $namespace) # Ignore terms not in specified namespace
    }
    $tot_count++;  # Add to count of total number of terms checked
    if ($stag->{def} =~ m/..+/) { # If the term has a def that matches regex
      $def_count++; 
      next # go to next term - don't bother checking whether term has equivalent class def
    }
    for (@{$obo_mtag->{$id}}) {
      if ($_->{estat} eq 'int') { # If stanza contains one or more intersection tags
	$EC_stat = 1  # The flag as having and equivalent class def.
      }
    }
    $EC_count++, if ($EC_stat); # Add to count of terms with no text def but having an EC def.
  }
}

my $tot_def = $EC_count+$def_count;  # All terms without a textual def but with an EC def are assumed to get an EC def automatically - and so are added to total count of dedined terms.
my $percent_def = ($tot_def/$tot_count)*100;
my $percent_def_rounded = sprintf("%.2f", $percent_def);  # Rounding to 2 sig figs.
print "Defined\tTotal\t\%\n$tot_def\t$tot_count\t$percent_def_rounded\n";
