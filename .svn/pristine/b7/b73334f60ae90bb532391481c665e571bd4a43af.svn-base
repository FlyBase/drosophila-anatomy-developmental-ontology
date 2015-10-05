#!/usr/bin/env perl -w
use strict;
use DBI;
use ChadoConnect;
require TAPget;

=pod

Makes dump of all gene expression data as pub, feature, anatomy, stage-range

usage ./gene_expression_dump.pl <DB name> > output_file.tsv

where DB name is a string identifying a database instance to connect to.  See doc for ChadoConnect.pm for details of available connections.

=cut

unless ($ARGV[0]) {
  print "Please specify a DB.  See ChadoConnect doc for details of available DBs";
  die
}


# make chado connection

my $dbh = ChadoConnect::make_con($ARGV[0]);

# First loop, modified from annotation_ref_gen_finder.pl, makes two hashes: $hash{fe_id}=fbex; $hash{fe_id}=out and array @fbex.

my %feid_out;
my %feid_fbex;
my %fbex;
print STDERR "*** Retrieving FBgn to FBex associations.***\n\n";
my $sth = $dbh->prepare('SELECT fe.feature_expression_id as feid, gene.name AS gene_name, gene.uniquename as fbgn, pub.miniref, pub.uniquename AS fbrf, e.uniquename as fbex
FROM feature_expression fe
JOIN expression e ON (e.expression_id=fe.expression_id)
JOIN pub ON (fe.pub_id=pub.pub_id) 
JOIN feature_relationship fr ON (fr.subject_id=fe.feature_id)
JOIN cvterm rel ON (fr.type_id=rel.cvterm_id)
JOIN feature gene ON (fr.object_id=gene.feature_id) 
WHERE rel.name=\'associated_with\'
AND gene.uniquename like \'FBgn%\' -- LIMIT 10'); # uncomment limit for debugging.
$sth->execute or die "WARNING: ERR: Unable to execute query\n";
while (my $hash_ref = $sth->fetchrow_hashref) {
  my $feid = $hash_ref->{feid};
  my $fbex = $hash_ref->{fbex};
  $feid_out{$feid} = "$hash_ref->{feid}\t$hash_ref->{gene_name}\t$hash_ref->{fbgn}\t$hash_ref->{fbrf}\t$hash_ref->{miniref}";
  push (@{$feid_fbex{$feid}}, $fbex); # Array of FBex for each 
  $fbex{$fbex}=1; # Unique list of expression statements, to avoid looking up anything multiple times in chado. 
}
#  $sth->finish; ### Probably not necessary as should set connection to inactive once all data is collected by while loop.  Commented out for now, as may be more useful to get warning of incomplete queries on disconnection.

# Make hash to send to TAPget.pm
my @fbex;
while (my ($key, $value) = each %fbex) {
  push @fbex, $key;
} 
# Take hash of fbex return datamodel 
my $number_exp_statements = scalar(@fbex);
print STDERR "*** Retrieving details of $number_exp_statements expression assertions (TAP statements). This may take a long time. Unparsable statements will be mentioned in STDERR ***\n\n";

my $TAP_dm = TAPget::get_TAP_data_model($dbh,\@fbex);  # But note - this works on names!

my $FBbtdv_name_id = roll_anatomy_stage_lookup($dbh);

# Output loop 
print STDERR "*** Printing gene expression details to STDOUT ***\n\n";
while (my ($feid, $fbex) = each %feid_fbex) {
  for (@{$fbex}) {
    print $feid_out{$feid};
    if ($TAP_dm->{$_}->{'anatomy'} && (exists $FBbtdv_name_id->{$TAP_dm->{$_}->{'anatomy'}})) {
      print "\t".$TAP_dm->{$_}->{'anatomy'}."\t".$FBbtdv_name_id->{$TAP_dm->{$_}->{'anatomy'}}
    } else {
      print "\torganism\t".$FBbtdv_name_id->{'organism'};  # If no anatomy specified - use 'organism'
    }
    if (exists $TAP_dm->{$_}->{'amp_stages'}) {  # If only one stage is recorded - put this in both start and end slots.
      if (@{$TAP_dm->{$_}->{'amp_stages'}} == 1) {
	my $s = pop(@{$TAP_dm->{$_}->{'amp_stages'}});
	$TAP_dm->{$_}->{'start_stage'} = $s;
	$TAP_dm->{$_}->{'end_stage'} = $s;
      }
    }	 
    if ($TAP_dm->{$_}->{'start_stage'} && (exists $FBbtdv_name_id->{$TAP_dm->{$_}->{'start_stage'}})) {
      print "\t".$TAP_dm->{$_}->{'start_stage'}."\t".$FBbtdv_name_id->{$TAP_dm->{$_}->{'start_stage'}}
    } else {
      print "\t\t"
    }
    if ($TAP_dm->{$_}->{'end_stage'} && (exists $FBbtdv_name_id->{$TAP_dm->{$_}->{'end_stage'}})) {
      print "\t".$TAP_dm->{$_}->{'end_stage'}."\t".$FBbtdv_name_id->{$TAP_dm->{$_}->{'end_stage'}}
    } else {
      print "\t\t"
    }
    print "\n"
  }
}

my $rc = $dbh->disconnect or warn $dbh->errstr; # May not be necessary, but could provide useful warning of incomplete SQL queries.


sub roll_anatomy_stage_lookup {
   # NOTE - RELIES ON UNIQUE NAME ASSUMPTION FOR anatomy+stage!
  my %FBbtdv_name_id;
  my $dbh =$_[0];
  my $sth = $dbh->prepare('SELECT c.name, dbx.accession, db.name as idp
 FROM cvterm c
 JOIN dbxref dbx ON (c.dbxref_id = dbx.dbxref_id)
 JOIN db ON (dbx.db_id = db.db_id)
 WHERE c.is_obsolete = \'0\' -- NOT IMPLEMENTED AS BOOLEAN IN CHADO!
 AND db.name in (\'FBbt\', \'FBdv\')');
  $sth->execute or die "WARNING: ERR: Unable to execute query\n";
  # Make perl data structure .
  while (my $hash_ref = $sth->fetchrow_hashref) {
    $FBbtdv_name_id{$hash_ref->{'name'}}= "$hash_ref->{'idp'}:$hash_ref->{'accession'}"
  }
  return \%FBbtdv_name_id
}
