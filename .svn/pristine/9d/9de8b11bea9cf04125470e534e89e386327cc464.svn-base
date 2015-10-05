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
  my $EC_stat = 0;
#  print "$id ; $stag->{name} ; $stag->{is_obsolete} \n";
  unless ($stag->{is_obsolete}) {
    if ($namespace) {
      next, unless ($stag->{namespace} eq $namespace)
    }
    $tot_count++;
    if ($stag->{def} =~ m/..+/) {
      $def_count++; 
      next
    }
    for (@{$obo_mtag->{$id}}) {
      if ($_->{estat} eq 'int') {
	$EC_stat = 1
      }
    }
    $EC_count++, if ($EC_stat);
  }
}

my $tot_def = $EC_count+$def_count;
my $percent_def = ($tot_def/$tot_count)*100;
my $percent_def_rounded = sprintf("%.2f", $percent_def);
print "Defined\tTotal\t\%\n$tot_def\t$tot_count\t$percent_def_rounded\n";
