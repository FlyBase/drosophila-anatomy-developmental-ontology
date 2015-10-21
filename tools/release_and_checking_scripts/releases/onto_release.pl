#!/usr/bin/env perl
use warnings;
use strict;

=pod 

=head1 use: onto_release.pl <ontology_name> <path to oort directory for build>

ontology_name is the short, lower case version of the OBO foundry IDSPACE e.g. fbbt, fbdv, fbcv

This script requires the output of an oort run in which the starting file has a data-version tag that follows the standard  pattern /YYYY-MM-DD\{\[a-z\]?$/

The script runs the following checks:


=over
=item
Is the oort directory empty?
=item                                                                                                                                                                                                                                                                                                                                                     
Does it contain a file called ontology_name-simple.obo?
=item                                                                                                                                                                                                                                                                                                    
Does it contain a folder named for the specified data-version tag=item
Does ontology_name-simple.obo have  


=cut

my $idp = $ARGV[0];
my $oort_path = $ARGV[1];

die "use $0 idp <oort path>" unless (@ARGV == 2);
die "Unknown idp, $ARGV[0], please use fbcv, fbdv or fbbt" unless (($ARGV[0] eq  'fbbt') || ($ARGV[0] eq 'fbcv') || ($ARGV[0] eq 'fbdv'));

# check whether build worked by seeing if oort dir is empty
my @oort = `ls $oort_path`;
die "$idp oort dir is empty, did Jenkins build fail?" unless (@oort);
# grab release data-version
## First open the smallest obo version:
open SIMPLE, "<$oort_path/$idp-simple.obo" or die "Can\'t find $oort_path/$idp-simple.obo ($!)\n"; # provides a useful check for failure of oort run
## Now iterate over it line by line looking for data-version. until the first blank line - as a quick way of limiting to header.

my $data_version = '';
while (<SIMPLE>) {
  chomp; # Is this needed?
  $data_version = $1 if m/^data-version\: (.+)/;
  last if ($data_version);	# Stop if data_version tag found
  last unless $_; 		# Stop after the header
}
close SIMPLE;


die "$oort_path/$idp-simple.obo has no data-version specified!" unless ($data_version);

#open SVERSION, "<$oort_path/releases/$data_version/$idp-simple.obo" or die "Can\'t find $oort_path/$idp-simple.obo"; # provides a check for version in oort.  Should never be tripped as oort contents should be blown away at start of build.
#close SVERSION;

# run regex test to see if data-version fits standard pattern
die "data-version, $data_version, does not follow standard pattern (YYYY-MM-DD\{\[a-z\]\})." unless ($data_version =~ m/\d{4}\-(\d{2})-(\d{2})[a-z]?$/);
# Basic sanity checks on date
die 'Month cannot be >12!' unless ($1 <= 12); 
die 'Day of Month >31!' unless ($1 <= 31); # Could do something fancy with data functions here, but can't be bothered.



# Check we're in the right dir for the release

# Make release.

# die; 				# Added for safety while testing.

# Can't use exec here as kill script. System seems a better bet, but still seeing problems trying ``

# Cleanest way to store releases:
# Copy new release files to /releases/.
# svn mkdir $data_version
# Then svn cp *.txt *.obo. *.
# The only danger in this is that it will propagate and drek that has accumulated in /releases/.  - We need a mechanism to check all content of this folder.

my %valid_release_files;
my $wlist_file_path = 'src/trunk/tools/'.$idp.'_release_file_whitelist';
open WLIST, "<$wlist_file_path" or die "Can't open whitelist file: $wlist_file_path ($!)\n";
while (<WLIST>) {
  chomp;
  next unless ($_);
  $valid_release_files{$_}=1
}

# Grab oort folder contents
open (OORT_LS, "ls  -p $oort_path/ |") or die "Can't run program $!\n";  # See Perl Cookbook pg 624 for explanation; ls -p writes a slash (`/') after each filename if that file is a directory
my %oort_folder_contents;
while (<OORT_LS>) {  #.
  chomp;
  next if (m/\/$/); # Ignore directories
  $oort_folder_contents{$_}=1
}

# Grab release folder contents
open (REL_LS, "ls  -p releases/ |") or die "Can't run program $!\n";  # See Perl Cookbook pg 624 for explanation; ls -p writes a slash (`/') after each filename if that file is a directory
my %release_folder_contents;
while (<REL_LS>) { 
  chomp;
next if (m/\/$/); # Ignore directories
  $release_folder_contents{$_}=1
}

# For each file on whitelist
# die if not in oort
# die if not in releases
# die if not under VC in releases folder
# For each file in releases folder - die if not on whitelist

#for (keys %valid_release_files) {
  #die "$_ is on the whitelist but not in $oort_path" unless (exists $oort_folder_contents{$_}); 
 # die "$_ is on the whitelist but  not in releases/" unless (exists $release_folder_contents{$_});   
 # my $svn_status = `svn status  releases/$_`;
  #die "$_ is on the whitelist  but is not under version control.  Please svn add this file manually and try again." if ($svn_status =~ /^\?/);
#}


for (keys %release_folder_contents) {
  # die "$_ is in the release folder but is not a valid release file name. Please remove or add to whitelist" unless exists ($valid_release_files{$_});
}

#die; # Safety catch while script debugged
`mkdir releases/$data_version`;

for (keys %valid_release_files) {
  `cp $oort_path/$_ releases/.`;  #copy whitelist files from oort to releases- overwrites what is there
  #`cp $oort_path/$_ releases/latest/.`;  #copy whitelist files from oort to releases/latest- overwrites what is there
  `cp releases/$_ releases/$data_version/.`; #copy whitelist files from oort to releases/data-version - without overwriting
}
`cp -r src/trunk src/tags/$data_version`;    #copy files from src/trunk to src/tags/data-version - without overwriting

# `svn commit -m'New release of $idp - $data_version, with tag set.' $idp`;  # Better to let user do final commit.

