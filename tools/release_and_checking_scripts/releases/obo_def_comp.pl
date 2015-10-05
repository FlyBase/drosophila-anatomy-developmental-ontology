#!/usr/bin/env perl -w
use strict;
require OboModel;

=pod

=head1 use

Script for finding modified definitions and comments between ontology versions. If a definition or comment is new or modified, it returns that definition.

Takes two argument:

1st argument = path to old file

2nd argument = path to new file

=head1 dependencies

Requires OboModel.pm to be in either Perl mod file path or same directory as script.

=cut


my ($obo_stag_old) = OboModel::obo_parse($ARGV[0]);
my ($obo_stag_new) = OboModel::obo_parse($ARGV[1]);

my ($id, $value);
while (($id, $value) = each %$obo_stag_new) {
  if ($value->{def}) {
    if ($obo_stag_old->{$id}->{def}) {
      if ($value->{def} ne $obo_stag_old->{$id}->{def}) {
	print "\n$value->{name} ; $id has a changed definition:\n$value->{def}\n"
      }
    } else {
      print "\n$value->{name} ; $id has a new definition:\n$value->{def}\n"
    }
  }
  if ($value->{comment}) {
    if ($obo_stag_old->{$id}->{comment}) {
      if ($value->{comment} ne $obo_stag_old->{$id}->{comment}) {
	print "\n$value->{name} ; $id has a changed comment:\n$value->{comment}\n"
      }
    } else {
      print "\n$value->{name} ; $id has a new comment:\n$value->{comment}\n"
    }
  }
}
