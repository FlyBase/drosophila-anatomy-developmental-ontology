#!/usr/bin/env perl -w
package ChadoConnect;
use strict;
use DBI;

our (@ISA, @EXPORT, $VERSION);

use Exporter;
$VERSION= 2.00;
@ISA = qw(Exporter);
@EXPORT= qw (make_con);
1;

=pod

usage:

$database_handle = ChadoConnect.make_con('DB name')

Available DB names: FB_public - connects to the open, public chado DB.

=cut 

sub make_con {
  my $dbh = '';
  if ($_[0] eq 'FB_public') {
    $dbh = DBI->connect("dbi:Pg:dbname=flybase;host=flybase.org;port=5432",'flybase' ,'')
  } else {
    print STDERR "Unrecognised DB $_[0].  Recognised DBs:  FB_public." ;
    die
  }
  return $dbh
}




