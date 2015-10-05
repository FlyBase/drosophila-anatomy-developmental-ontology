 #!/usr/bin/env perl -w
package TAPget;
use strict;

our (@ISA, @EXPORT, $VERSION);

use Exporter;
$VERSION= 2.00;
@ISA = qw(Exporter);
@EXPORT= qw (&get_TAP_data_mode &roll_TAP);
1;

=pod

=head1 TAPget.pm, a module for rolling TAP data models and TAP strings

A module for connecting to chado and rolling data models of complete TAP statements and, optionally, TAP statement strings.  It has two methods:

get_TAP_data_model takes two arguments, the first a path to modules.cfg, required for connection to chado, and the second an array of fbex (e.uniquename).  It returns a reference to a hash containing the TAP data model.

The hash structure is

 $exid_TAP{$ex_id}{anatomy} = $hash_ref->{cvt}
 $exid_TAP{$ex_id}{anatomy_of}->[$rank]=$hash_ref->{cvt}
 $exid_TAP{$ex_id}{anat_q}->[$rank]=$hash_ref->{cvt}
 $exid_TAP{$ex_id}{assay} = $hash_ref->{cvt}
 $exid_TAP{$ex_id}{cc} = $hash_ref->{cvt}
 $exid_TAP{$ex_id}{start_stage} = $hash_ref->{cvt}
 $exid_TAP{$ex_id}{end_stage} = $hash_ref->{cvt}
 $exid_TAP{$ex_id}{amp_stages}->[$rank]->{$hash_ref->{cvt}
 $exid_TAP{$ex_id}{stage_q}->[$rank]=$hash_ref->{cvt}
 $exid_TAP{$ex_id}{cc_q}->[$rank]=$hash_ref->{cvt}

Note that this is data structure differs from that in version 1.0 (see below) in having  $exid_TAP{$ex_id}{amp_stages}->[$rank]->{$hash_ref->{cvt}

It should be backwards compatible with version 1.0 as it retains 

 $exid_TAP{$ex_id}{start_stage} = $hash_ref->{cvt}
 $exid_TAP{$ex_id}{end_stage} = $hash_ref->{cvt}

roll_TAP takes two arguments - The first is an array of fbex, the second is a reference to the datamodel rolled by get_TAP_data_model.  It returns a hash of fbex => 'TAP statement'.

Improvements to this method over version 1.0:
Fixed interdependence of assay and stage fields (could potentially have been a cause of rare bugs)
output now uses TAP syntax for stage range and anatomy intersections.

=head2 Known limitations:

Associativity of stage qualifiers to stages is likely to be screwed up in statements that contain multiple stage terms.  All qualifiers are listed at the end.  Fixing this is not trivial.

TAP model and rolling will fail with a warning if it has > 2 anatomy terms.

=head2 Notes on future improvements

Parsing efforts so far have been focussed on semantics.  It is probably more straightforward to achieve complete parsing by extracting a syntactical model.  Translation to a semantic model could then happen under the hood.  Could do all of these as objects.


expression object
assay
anatomy object - includes qualifiers?
stage object - includes qualifiers, but does it include sex?



=head2 appendices

=head3 version 1 data model

This is the hash structure of the version 1 data model

 $exid_TAP{$ex_id}{anatomy} = $hash_ref->{cvt}
 $exid_TAP{$ex_id}{anatomy_of}->[$rank]=$hash_ref->{cvt}
 $exid_TAP{$ex_id}{anat_q}->[$rank]=$hash_ref->{cvt}
 $exid_TAP{$ex_id}{assay} = $hash_ref->{cvt}
 $exid_TAP{$ex_id}{cc} = $hash_ref->{cvt}
 $exid_TAP{$ex_id}{start_stage} = $hash_ref->{cvt}
 $exid_TAP{$ex_id}{end_stage} = $hash_ref->{cvt}
 $exid_TAP{$ex_id}{stage_q}->[$rank]=$hash_ref->{cvt}
 $exid_TAP{$ex_id}{cc_q}->[$rank]=$hash_ref->{cvt}


It was retired because it is possible for TAP statements to have two or more stages specified where none is specified as a start or end stage.  Its replacement should be backwards compatible, as it retains the start and end stage

=cut


# method takes 2 arguments - path to a config file for connection to chado and an array of ex_ids. (note $ex_id here = expression.uniquename - might better be called fbex

sub get_TAP_data_model {
  my $dbh =  $_[0];
  my %exid_TAP;
  my $ex_ids = $_[1];
  my $in_string;
  while (@{$ex_ids}) {
    my $ex_id = pop(@{$ex_ids});
    $in_string .= "\'$ex_id\'";
    $in_string .= ', ' if ((@{$ex_ids} >= 1))
  }  # Is there some upper limit on how many things can be referenced in an in?

  my %anat_count;  # counter for # anatomy terms for error checking.  Probably worth adding more of these.
  my $sth = $dbh->prepare("SELECT c.name as cvt, 
ec.rank as ec_rank, 
t1.name as ec_type, 
ectp.value as ectp_value, 
t2.name as ectp_name, 
ectp.rank as ectp_rank,
e.uniquename as fbex
FROM expression_cvterm ec
JOIN expression e on ec.expression_id=e.expression_id
LEFT OUTER JOIN expression_cvtermprop ectp on ec.expression_cvterm_id=ectp.expression_cvterm_id 
JOIN cvterm c on ec.cvterm_id=c.cvterm_id 
JOIN cvterm t1 on ec.cvterm_type_id=t1.cvterm_id 
LEFT OUTER JOIN cvterm t2 on ectp.type_id=t2.cvterm_id
WHERE e.uniquename in ($in_string)");  
  $sth->execute or die "WARNING: ERR: Unable to execute query\n";

# Make a perl data structure for each TAP statement.
  while (my $hash_ref = $sth->fetchrow_hashref) {
    my $ex_id = $hash_ref->{fbex};
    $exid_TAP{$ex_id}{assay} = $hash_ref->{cvt}, if ($hash_ref->{ec_type} eq 'assay');
    
    $exid_TAP{$ex_id}{start_stage} = $hash_ref->{cvt}, if (($hash_ref->{ec_type} eq 'stage')&&($hash_ref->{ectp_value})&&($hash_ref->{ectp_value} eq 'FROM'));  # Changed from version 1.0, which was designed to put stages from TAP statements with single stage in 'start_stage'. These now go in the new amp_stages array.

    if (($hash_ref->{ec_type})&&($hash_ref->{ectp_name})&&($hash_ref->{ec_type} eq 'stage')&&($hash_ref->{ectp_name} eq 'qualifier')) {
      my $rank = ($hash_ref->{ec_rank});
      $exid_TAP{$ex_id}{stage_q}->[$rank]=$hash_ref->{cvt}
    }

    $exid_TAP{$ex_id}{end_stage} = $hash_ref->{cvt}, if (($hash_ref->{ec_type})&&($hash_ref->{ectp_value})&&($hash_ref->{ec_type} eq 'stage')&&($hash_ref->{ectp_value} eq 'TO'));

    if (($hash_ref->{ec_type} eq 'stage')&&(!($hash_ref->{ectp_value})&&(!$hash_ref->{ectp_name}))) { #Note - test needs to be for null here, rather than exists.
      my $rank = ($hash_ref->{ec_rank});
      $exid_TAP{$ex_id}{amp_stages}->[$rank]= $hash_ref->{cvt}; 
    }
    
    if (($hash_ref->{ec_type} eq 'anatomy')&&(!$hash_ref->{ectp_value})&&(!$hash_ref->{ectp_name})) {
      $exid_TAP{$ex_id}{anatomy} = $hash_ref->{cvt};
      $anat_count{$ex_id}++;
    }
    
    if  (($hash_ref->{ec_type})&&($hash_ref->{ectp_name})&&($hash_ref->{ec_type} eq 'anatomy')&&($hash_ref->{ectp_name} eq 'qualifier')) {
      my $rank = ($hash_ref->{ec_rank});
      $exid_TAP{$ex_id}{anat_q}->[$rank]=$hash_ref->{cvt};
    }
    
    if (($hash_ref->{ec_type})&&($hash_ref->{ectp_value})&&($hash_ref->{ec_type} eq 'anatomy')&&($hash_ref->{ectp_value} eq 'OF')) {
      my $rank = ($hash_ref->{ec_rank});
      $exid_TAP{$ex_id}{anatomy_of}->[$rank]=$hash_ref->{cvt};
      $anat_count{$ex_id}++;
    }
    
    $exid_TAP{$ex_id}{cc} = $hash_ref->{cvt}, if(($hash_ref->{ec_type} eq 'cellular'));
    if (($hash_ref->{ec_type})&&($hash_ref->{ectp_value})&&($hash_ref->{ec_type} eq 'cellular')&&($hash_ref->{ectp_name} eq 'qualifier')) {
      my $rank = ($hash_ref->{ec_rank});
      
      $exid_TAP{$ex_id}{cc_q}->[$rank]=$hash_ref->{cvt}
    }
  }
  for (my ($key, $value) = each %anat_count) {
    if ($value > 2) {
      &cant_cope($key, 'more than 2 anatomy terms');
      $exid_TAP{$key}=0
    }

  }
  return (\%exid_TAP)
    # $rc = $dbh->disconnect or warn $dbh->errstr; # It is now the responsibility of the calling script to close the database handle.   
}


# Method takes two arguments: first arg is array of IDs. Second arg is TAP data model as $exid_TAP;


# notes on version 2 - have improved the TAP roller, eliminating dependence between elements (a bad move in version 1) and adding code to deal with amplists of stage terms.  However, stage qualifiers are not dealt with properly.  Right now, they all get glommed at the end of the stage, rather than associating with the stage to which they apply.  This could probably be solved for amplists by glomming stage and qualifiers together into one array and using rank to sort (but remember - rank is stored as array position!).  Even more difficult to solve for start and end stages.

sub roll_TAP {
  my %exid_TAP_statement;
  my $exid_TAP = $_[1];
  my $exids = $_[0];
  my $ex_id='';
  my $feat='';
  for $ex_id (@{$exids}) {
    if (!$exid_TAP->{$ex_id}) {
      warn 'Bad tap model for $ex_id'
    } else {
      my $TAP = '<e> ';
      $TAP .= "$exid_TAP->{$ex_id}->{assay}", if (exists $exid_TAP->{$ex_id}->{assay});
      $TAP .= ' <t> ';
      $TAP .= "$exid_TAP->{$ex_id}->{start_stage}", if (exists $exid_TAP->{$ex_id}->{start_stage});
      $TAP .= "--$exid_TAP->{$ex_id}->{end_stage}", if (exists $exid_TAP->{$ex_id}->{end_stage});
      if (exists $exid_TAP->{$ex_id}->{amp_stages}) {
	my @stages = @{$exid_TAP->{$ex_id}->{amp_stages}};
	while (@stages) {
	  $TAP .= shift (@stages);
	  $TAP .= " & ", if (@stages >= 1);
	}
      }
      $TAP .= &TAP_q($exid_TAP->{$ex_id}->{stage_q}), if ($exid_TAP->{$ex_id}->{stage_q});
      $TAP .= ' <a> ';
      $TAP .= $exid_TAP->{$ex_id}->{anatomy}, if ($exid_TAP->{$ex_id}->{anatomy});
      if ($exid_TAP->{$ex_id}->{anatomy_of}) {
	for (@{$exid_TAP->{$ex_id}->{anatomy_of}}) {
	  $TAP .= " &&of $_", if ($_);
	}
      }
      $TAP .= &TAP_q($exid_TAP->{$ex_id}->{anat_q}), if ($exid_TAP->{$ex_id}->{anat_q});
      $TAP .= ' <s> ';
      $TAP .= $exid_TAP->{$ex_id}->{cc}, if ($exid_TAP->{$ex_id}->{cc}) ;
      $TAP .= &TAP_q($exid_TAP->{$ex_id}->{cc_q}), if ($exid_TAP->{$ex_id}->{cc_q});
      $TAP .= ' <note> ';
      $exid_TAP_statement{$ex_id}=$TAP
    }
  }
return (\%exid_TAP_statement)
}

# sub get_simple_exp_pdm {
#   my $FBbtdv_name_id = &roll_anatomy_stage_lookup();
#   my %exid_out;
#   my $exid_TAP = $_[1];
#   my $exids = $_[0];
#   my $ex_id='';
#   my $feat='';
#   for $ex_id (@{$exids}) {
#     if (!$exid_TAP->{$ex_id}) {
#       warn 'Bad tap model for $ex_id'
#     } else {
#       if ($exid_TAP->{$ex_id}->{anatomy}&& $exid_TAP->{$ex_id}->{'start_stage'}&&$exid_TAP->{$ex_id}->{'end_stage'}) { # Ignore everything without start and end stages specified
#         $exid_out{$ex_id} =  { 'anatomy_name'  => $exid_TAP->{$ex_id}->{anatomy},
#                                'anatomy_id' =>  $FBbtdv_name_id->{$exid_TAP->{$ex_id}->{anatomy}},
#                                'start_stage_name'  => $exid_TAP->{$ex_id}->{start_stage},
#                                'start_stage_id' =>  $FBbtdv_name_id->{$exid_TAP->{$ex_id}->{start_stage}},
#                                'end_stage_name'  => $exid_TAP->{$ex_id}->{end_stage},
#                                'end_stage_id' =>  $FBbtdv_name_id->{$exid_TAP->{$ex_id}->{end_stage}}
#                               }
#       }
#     }
#   }
# }
      


# Subroutine to roll lists of qualifiers in which first term is separated from main term (<t> <a> or <s>) by a pipe and all subsequent terms are separated by ampersands.  Note - this is purely syntax - AFAIK, no semantics involved.
sub TAP_q {
  my $TAP_q = ' | ';
  my @qual = @{$_[0]};
  while (@qual > 0) {
    my $q = '';
    $q = shift @qual;
    $TAP_q .= $q, if ($q);
    $TAP_q .= " & ", if ((@qual >= 1)&&($q));
  }
return $TAP_q;
}


sub cant_cope {
  warn "TAP roller has done its best with can't cope with TAP statement $_[0] as it has $_[1]. You may wish to investigate further."
}

