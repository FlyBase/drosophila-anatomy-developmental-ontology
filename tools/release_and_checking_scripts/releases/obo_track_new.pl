#!/usr/bin/perl -w
use strict;
use OboModel;

=pod

=head1 obo_track_new_rf.pl

=head2 use obo_track_new_rf.pl <path to old obo file> <path to new obo file>

=head2 requires OboModel.pm

=head2 Summary

Loops through terms from the old file and looks at what has happened to their names and IDs. Gives a chatty output describing their fate, if any.

=head2 Sketch of how it works

=over 1

=item 1. If term is obsolete in old file, check next term.

=item 2. Check if old id is still a primary id.

=item 2.1 If old id is no longer primary, is it an alt_id?

=item 2.1.1 If old id is an alt id, check if old name retained as synonym

=item 2.1.1.1 If old id is alt_id, is it an alt_id for an obsolete term?

=item 2.1.1.1.1 If old id is an alt_id for an obs term are there consider/replace suggestions

=item 2.1.2 If merged, print report on merged term

=item 2.2 If old id is not primary or secondary ID, report ID as lost:

=item 2.3. If old ID is primary, check if term has term been obsoleted

=item 2.3.1 If term has been obsoleted, check if has consider term

=item 2.3.2 If obs, print obs term report

=item 2.4 If old id is not obsolete, has its name changed?

=item 2.4.1 If name changed, has its old name been retained as a synonym?

=item 2.4.2  If name changed, print name change report

=back

=cut

# Notes on structure: 
### Bit oddly refactored. Rather than making subroutines, it would probably be better to roll more bespoke data structures at the start and call these during the check and print routine. e.g. could make $new_id_consider{$id}=@consider and $new_id_obstat{$id}=$obstat.  This would speed script up alot too.

my ($obo_stag_old, $obo_mtag_old) = OboModel::obo_parse($ARGV[0]);
my ($obo_stag_new, $obo_mtag_new) = OboModel::obo_parse($ARGV[1]);

my ($old_id, $old_value, $new_id, $new_value) ='';

my %new_alt_id;
#
while (($new_id, $new_value) = each %$obo_mtag_new) { 
  for (@{$new_value}) {
    $new_alt_id{$_->{obj}}=$new_id, if ($_->{estat} eq 'alt_id')
  }
}

my $dropped_id_flag = 0;

while (($old_id, $old_value) = each %$obo_stag_old) {
  next, if ($old_value->{is_obsolete}); # 1. If term is obsolete in old file, check next term
  my $merge_term = '';
  my $syn_stat = 0;
  my $obs_stat = 0;
  my $consider_or_rep_term = '';
  # 2. Check if old id is still a primary id.
  if (!(exists ($obo_stag_new->{$old_id}))) { 
    # 2.1 If old id is no longer primary, is it an alt_id?
    $merge_term = $new_alt_id{$old_id}, if (exists ($new_alt_id{$old_id})); 
    # 2.1.1 If old id is an alt id, check if old name retained as synonym
    for (@{$obo_mtag_new->{$merge_term}}) {
      if (($_->{estat} eq 'syn')&&($_->{an} eq $old_value->{name})) {
	$syn_stat = 1 
      } elsif (($_->{estat} eq 'syn')&&($_->{an} =~ m/$old_value->{name}/)) {
	$syn_stat = $_->{an}
      }
    }
    # 2.1.1.3 If old id is alt_id, is it an alt_id for an obsolete term and if so does if have consider suggestions?
    my ($obs_stat, $consider_or_rep_term) = (&obsolete_and_consider_or_rep ($merge_term));  
    # print reports for merged terms
    if ($merge_term) {
      print "$old_value->{name} ; $old_id has been merged with $obo_stag_new->{$merge_term}->{name} ; $merge_term.";    
      if ($syn_stat) {
	print " The merged term retains the old term name as a synonym."
      } else { 
	print " The old term name has not been retained as a synonym of the merged term."
      } 
      if ($obs_stat) {
	print " The merged term is obsolete.";
	if ($consider_or_rep_term) {
	  &consider_print($consider_or_rep_term);
	  } else {
	    print " This obsolete term has no suggested alternative terms."
	  }
      }
      print "\n";
#       2.1.2 If old id is not primary or secondary ID, report ID as lost:
    } else {
      print "$old_value->{name} ; $old_id has been lost!\n";
      $dropped_id_flag = 1;
    }
#        2.1.3. If old ID is primary, check if term has term been obsoleted
  } else {
    ($obs_stat, $consider_or_rep_term) = (&obsolete_and_consider_or_rep($old_id));
    if ($obs_stat) {
      print "$old_value->{name} ; $old_id has been made obsolete. ";
#      2.2.3.1 If term has been obsoleted, check yes, check if has consider term(s)

      if (@{$consider_or_rep_term}) {
	&consider_print($consider_or_rep_term);
      } else {
	print " This obsolete term has no suggested alternative terms."
      }
      print "\n"
#       2.3.2 If old id is not obsolete, has its name changed
    } elsif ($old_value->{name} ne $obo_stag_new->{$old_id}->{name}) {
      print "$old_value->{name} ; $old_id has changed name to $obo_stag_new->{$old_id}->{name}. ";
      $syn_stat = 0;
      for (@{$obo_mtag_new->{$old_id}}) {
	if (($_->{estat} eq 'syn')&&($_->{an} eq $old_value->{name})) {
	  $syn_stat = 1 
	} elsif (($_->{estat} eq 'syn')&&($_->{an} =~ m/$old_value->{name}/)) {
	  $syn_stat = $_->{an}
	}
      }
      if (!$syn_stat) {
	print "The old name is not a synonym.\n"
      
      } elsif ($syn_stat eq 1) {
	print "The old name is a synonym.\n"
      } else {
	print "The old name is a substring of a synonym: $syn_stat\n"
      }
    }
  }
}

die "\nDropped IDs!\n", if ($dropped_id_flag);
1;

# sub synonym {
#   my $synstat = 0;
#   for (@{$obo_mtag_new->{$old_id}}) {
#     $synstat = 1, if (($_->{estat} eq 'syn')&&($_->{an} eq $old_value->{name}))
#   }
#   if ($synstat) {
#     print "The old name is a synonym.\n"
#   } else {
#     print "The old name is not a synonym.\n"
#   }
# }

sub consider_print {
  my $in = $_[0];
  my  @con = @{$in};
  print "Suggested alternative term(s): ";
  while (@con) {
    my $con = pop (@con);
    print "$obo_stag_new->{$con}->{name} ; $con";
    print ", ", if (@con >= 1);
  } 
}

sub obsolete_and_consider_or_rep {
  my $id = $_[0];
  my $ostat = 0;
  if ($obo_stag_new->{$id}->{is_obsolete}) {
    $ostat = 1;
    my @con = ();
    for (@{$obo_mtag_new->{$id}}) {
      push @con, $_->{obj}, if (($_->{estat} eq 'consider')||($_->{estat} eq 'replaced_by'))
    }
    return ($ostat, \@con)
  }
}
