#!/usr/bin/env perl -w
package OboModel;
use strict;

our (@ISA, @EXPORT, $VERSION);

use Exporter;
$VERSION= 1.00;
@ISA = qw(Exporter);
@EXPORT= qw (&obo_parse);
1;

# TODO - extend to break down relations
#########################

sub obo_parse {
  my $file = $_[0];
  my ($terms, $obo_relations, $obo_header) = &obo_chop(&slurp($file));
  my ($obo_stag, $obo_mtag, $obo_stanza)= &obo_array($terms, $$obo_header);
  return ($obo_stag, $obo_mtag, $obo_stanza, $obo_relations, $obo_header);
}


sub obo_array {
  my %obo_stags;
  my %obo_mtags;
  my %obo_stanzas;
  my $terms = shift;
  my $header = shift;
  my ($anonymous, $obsolete, $default_namespace) = 0;
  $default_namespace = $1, if ($header =~ m/default\-namespace\: (.+)/); 
  my @term = @{$terms};
  foreach (@term) {
    my $subject_id = $1, if ($_ =~ m/id\: (\S+)/);
    $obo_stanzas{$subject_id} = $_; # initialise stanza
    warn "The syntax of the ID $subject_id does not follow OBO foundry convention for OBO IDs!" unless ($subject_id =~ m/^\w+:\d+$/);
    my $subject_name = $1, if ($_ =~ m/name\: (.+)/);
    my $namespace = '';
    if ($_ =~ m/\nnamespace\: (.+)/) {
      $namespace = $1;
    } else {
      $namespace = $default_namespace
    }
    my $comment = '';
    $comment = $1, if ($_ =~ m/comment\: (.+)/);
    my $creation_date = '';
    $creation_date = $1, if ($_ =~ m/creation_date\: (.+)/);
    my $created_by = '';
    $created_by = $1, if ($_ =~ m/created_by\: (.+)/);
    if ($_ =~ m/is_anonymous\: true/) { 
      $anonymous = 1
    } else {
      $anonymous = 0
    }
    if ($_ =~ m/is_obsolete\: true/) {
      $obsolete = 1 
   } else {
     $obsolete = 0
   }
    my $def = '';
    my $def_dbxrefs = '';
    my $def_dbxref_desc_stat = 0;
    if ($_ =~ m/def\: \"(.+)\" \[(.*)\]/) {
      $def =  $1;
      $def_dbxrefs = $2;
      $def_dbxref_desc_stat = 1, if ($def_dbxrefs =~ m/ \".+\"/);
      $def_dbxrefs =~ s/ \".+?\"//g;     #Strips out descriptions in quotes.
    }
    my @def_dbxrefs = split /, /, $def_dbxrefs;
    $obo_stags{$subject_id}={ name => $subject_name, def => $def, def_dbxref => $def_dbxrefs, def_dbxref_array => \@def_dbxrefs, def_dbxref_dstat => $def_dbxref_desc_stat, comment => $comment, namespace => $namespace, is_anonymous => $anonymous, is_obsolete => $obsolete, created_by => $created_by, creation_date => $creation_date};
    my @ir =();
    my @v=split(/\n/,$_);
    foreach(@v) {
# Warn of unknown tags with STDERR
     print STDERR "Unrecognized tag \"$_\"\n", unless ($_ =~ m/^name\: |^id\: |^namespace\: |^def\: |^comment\: |^intersection_of\: |^relationship\: |^xref\: |^synonym\: |^is_a\: |^subset\: |^union_of\: |^is_obsolete\: |^is_anonymous\: |^disjoint_from\: |^alt_id\: |^consider\: |^replaced_by\: |^creation_date\: |^created_by\: |^exact_synonym\: |^broad_synonym\: |^narrow_synonym\: |^related_synonym\: |^xref_analog\: |^equivalent_to\: /);
     print STDERR "Badly formated relationship: $_\n", if (($_ =~ m/(intersection|is_a)\: \w+\:\d+/) && (!($_ =~ m/(intersection|is_a)\: \w+\:\d+( \!|$)/)));
     print STDERR "Badly formated relationship: $_\n", if (($_ =~ m/(intersection|relationship)\:  \S+ \w+\:\d+/) && (!($_ =~ m/(intersection|is_a)\: \S+ \w+\:\d+( \!|$)/)));
     push @ir, { estat => 'rel', rel => $1, obj => $2, an =>'', axref => '' }, if ($_ =~ m/relationship\: (\S+) (\w+\:\d+)/);
     push @ir, { estat => 'int', rel => $1, obj => $2, an => '', axref => '' }, if ($_ =~ m/intersection_of\: (\S+) (\w+\:\d+)/);
     push @ir, { estat => 'int', rel => 'is_a', obj => $1, an => '', axref => '' }, if ($_ =~ m/intersection_of\: (\w+\:\d+)/);
     push @ir, { estat => 'rel', rel => 'is_a', obj => $1, an => '', axref => '' }, if ($_ =~ m/is_a\: (\w+\:\d+)/);
     push @ir, { estat => 'syn', rel => '', obj => '', an => $1, axref => $2 }, if ($_ =~ m/synonym\: \"(.+)\" \[(.*)\]/);
     push @ir, { estat => 'syn', rel => $2, obj => '', an => $1, axref => $3 }, if ($_ =~ m/synonym\: \"(.+)\" (.+) \[(.*)\]/);
     push @ir, { estat => 'subset', rel => '', obj => '', an => $1, axref => '' }, if ($_ =~ m/subset\: (.+)/);
     push @ir, { estat => 'xref', rel => '', obj => '', an => $1, axref => '' }, if ($_ =~ m/xref\: (.+)/);
     push @ir, { estat => 'union_of', rel => '', obj => $1, an => '', axref => '' }, if ($_ =~ m/union_of\: (\w+\:\d+)/);
     push @ir, { estat => 'alt_id', rel => '', obj => $1, an => '', axref => '' }, if ($_ =~ m/alt_id\: (\w+\:\d+)/);
     push @ir, { estat => 'disjoint_from', rel => '', obj => $1, an => '', axref => '' }, if ($_ =~ m/disjoint_from\: (\w+\:\d+)/);
     push @ir, { estat => 'consider', rel => '', obj => $1, an => '', axref => '' }, if ($_ =~ m/consider\: (\w+\:\d+)/);
     push @ir, { estat => 'replaced_by', rel => '', obj => $1, an => '', axref => '' }, if ($_ =~ m/replaced_by\: (\w+\:\d+)/);
     push @ir, { estat => 'equivalent_to', rel => '', obj => $1, an => '', axref => '' }, if ($_ =~ m/equivalent_to\: (\w+\:\d+)/);
   }
    $obo_mtags{$subject_id} = \@ir;
  } 
  return (\%obo_stags, \%obo_mtags, \%obo_stanzas)
}

# WARNING - this fails to comply with  some aspects of the field order spec for OBO 1.2 and 1.4.  Resulting file should be reserialised through some compliant tool (OE, owltools) before diff.

sub obo_print {
  my $obo_stag = $_[0];
  my $obo_mtag = $_[1];
  my $obo_stanza = $_[2];
  my $obo_relations = $_[3];
  my $obo_header = $_[4];
  my ($key, $value) = '';
  print $$obo_header;

### start change to existing code - changed while loop to foreach loop with assignment of $value
  foreach my $key (%{$obo_stag}) {
    my $value = $obo_stag->{$key};
#  while (($key, $value) = each %$obo_stag) {
### end change to existing code

    print "\n\n".'[Term]
id: '.$key;
    print '
namespace: '.$value->{namespace},if ($value->{namespace});
    print '
name: '.$value->{name};
    print '
def: "'.$value->{def}.'" ['.$value->{def_dbxref}.']',if (($value->{def})&&($value->{def_dbxref}));
    print '
def: "'.$value->{def}.'" []',if (($value->{def})&&(!$value->{def_dbxref}));
    print '
comment: '.$value->{comment},if ($value->{comment});
    print'
is_anonymous: true', if ($value->{is_anonymous});
    print'
is_obsolete: true', if ($value->{is_obsolete});
      print "\ncreated_by: ".$value->{'created_by'}, if ($value->{'created_by'});
      print "\ncreation_date: ".$value->{'creation_date'}, if ($value->{'creation_date'});

### start change to existing code - have added if loop here to check $obo_mtag->{$key} exists as
### I wondered if that might be causing the problem if there was a case where it doesn't exists even when $obo_stag->{$key} does.
    if (exists $obo_mtag->{$key}) {
### then have changed for to foreach, which doesn't really matter except that is the form I'm more familiar with
### have indented everything by two characters so it lines up properly
      foreach (@{$obo_mtag->{$key}}) {
#    for (@{$obo_mtag->{$key}}) {
### end change to existing code
        if ($_->{'estat'} eq 'rel') {
          if ($_->{'rel'} eq 'is_a') {
            print "\nis_a\: ".$_->{'obj'}.' ! '.$obo_stag->{$_->{'obj'}}->{name}
          } else {
            print "\nrelationship: ".$_->{rel}.' '.$_->{obj}.' ! '.$obo_stag->{$_->{obj}}->{name}
          }
        }
        if ($_->{estat} eq 'int') {
          if ($_->{rel} eq 'is_a') {
            print "\nintersection_of: ".$_->{obj}.' ! '.$obo_stag->{$_->{obj}}->{name}
          } else {
            print "\nintersection_of: ".$_->{rel}.' '.$_->{obj}.' ! '.$obo_stag->{$_->{obj}}->{name}
          }
        }
        print "\nalt_id: ".$_->{obj}, if ($_->{estat} eq 'alt_id');
        print "\ndisjoint_from: ".$_->{obj}, if ($_->{estat} eq 'disjoint_from');
        print "\nxref: ".$_->{an}, if ($_->{estat} eq 'xref');
        print "\nsynonym: \"".$_->{an}.'" '.$_->{rel}.' ['.$_->{axref}.']', if (($_->{estat} eq 'syn')&&($_->{rel})&&($_->{axref}));
        print "\nsynonym: \"".$_->{an}.'" '.$_->{rel}.' []', if (($_->{estat} eq 'syn')&&($_->{rel})&&(!$_->{axref})); # not all have xrefs
#      print "\nsynonym: \"".$_->{an}.'" ['.$_->{axref}.']', if (($_->{estat} eq 'syn')&&(!$_->{rel})&&($_->{axref})); # but all should be scoped
        print "\nsynonym: \"".$_->{an}.'" []', if (($_->{estat} eq 'syn')&&(!$_->{rel})&&(!$_->{axref}));
        print "\nsubset: ".$_->{an}, if ($_->{estat} eq 'subset');
        print "\nunion_of: ".$_->{obj}.' ! '.$obo_stag->{$_->{obj}}{name}, if ($_->{estat} eq 'union_of');
        print "\nconsider: ".$_->{obj}.' ! '.$obo_stag->{$_->{obj}}{name}, if ($_->{estat} eq 'consider');
        print "\nreplaced_by: ".$_->{obj}.' ! '.$obo_stag->{$_->{obj}}{name}, if ($_->{estat} eq 'replaced_by');
      }
### start change to existing code - end of loop of new if loop created above
    }
### end change to existing code
  }
  for (@{$obo_relations}) {
    print '

[Typedef]
'.$_
    }
print "\n";
}

sub obo_chop {
my $obo = $_[0];
my @term = split /\n\[Term\]\n/, $obo;
chomp (@term);
my $header = (shift @term);
my $relations = (pop @term);
my @rel = split /\n\[Typedef\]\n/, $relations;
chomp (@rel);
push @term, (shift @rel);
return (\@term, \@rel, \$header);
}

sub slurp
{
	local $/;
	open SLURP, $_[0] or die "Can't open target $_[0]\n";
	my $obo = <SLURP>;
	close SLURP or die "cannot close target $_[0]\n";
	warn "Warning - this OBO file has multiple newlines at the end. This will crash Peeves!", if ($obo =~ m/\n\n\n\z/);
	return $obo;
}
