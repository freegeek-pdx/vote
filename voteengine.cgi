#!/usr/bin/perl

package MyUtils;

our $css = '/~ryan52/style.css';

sub hoomanize {
    my $s = shift;
    $s =~ s/_/ /g;
    return $s;
}

sub dehoomanize {
    my $s = shift;
    $s =~ s/ /_/g;
    return $s;
}

package Vote;


my $engine = "/home/ryan52/voteengine-0.99/voteengine.py";
my $dir = "/root/votes/";

use File::Basename qw(basename);
use File::Spec qw(catfile);

use strict;
use warnings;

sub list_votes {
  my $DIR;
  opendir($DIR, $dir) or die $!;
  my @list;
  while (my $file = readdir($DIR)) {
    next if ($file =~ /^\./);
    push @list, $file;
  }
  closedir($DIR);
  return @list;
}

sub load {
  my $class = shift;
  my $name = shift;

  my $self = {};

  return unless grep $name, @{[$class->list_votes]}; # protect against evil

  $self->{fname} = File::Spec->catfile($dir, $name);
  $self->{name} = $name;

  bless $self, $class;

  $self->parse;

  return $self;
}

sub new {
  my $class = shift;
  my $name = shift;
  my $number_cands = shift;

  my $self = {};

  $self->{fname} = File::Spec->catfile($dir, $name);
  $self->{name} = $name;

  bless $self, $class;

  $self->{method} = $self->default_method;
  my @votes = ();
  $self->{votes} = \@votes;

  $self->{descriptions} = {};
  $self->{description} = "";

  $self->_set_num_cands($number_cands);

  return $self;
}

sub _set_num_cands {
    my ($self, $number_cands) = @_;

    my @c = ();
    foreach(1 .. $number_cands) {
	push @c, chr(64 + $_);
    }
    $self->{cands} = \@c;
    return;
}

sub number_votes {
  my $self = shift;
  my $count = 0;
  foreach(@{$self->{votes}}) {
      $count++ if(ref($_) eq "Vote::Individual");
  }
  return $count;
}

sub number_cands {
  my $self = shift;
  if(defined($self->{cands})) {
    my $list = $self->{cands};
    return scalar(@$list);
  } else {
    return 0;
  }
}

sub update_cands {
    my ($self, $number_cands) = @_;
    _set_num_cands(@_);
    foreach my $v(@{$self->{votes}}) {
	$v->{cands} = $self->{cands};
	$v->updated;
    }
}

sub add_vote {
  my $self = shift;
  my $v = Vote::Individual->new($self->{cands});
  push @{$self->{votes}}, $v;
  return $v;
}

sub remove_vote {
  my $self = shift;
  my $lookfor = shift;
  my $i = 0;
  foreach(@{$self->{votes}}) {
    if(defined($_->{ref}) && $_->{ref} eq $lookfor) {
      delete @{$self->{votes}}[$i];
    } else {
      $i ++;
    }
  }
}

sub edit_vote {
  my $self = shift;
  my $lookfor = shift;
  foreach(@{$self->{votes}}) {
    return $_ if(defined($_->{ref}) && $_->{ref} eq $lookfor);
  }
  return;
}

sub add_or_edit_vote {
  my $self = shift;
  my $lookfor = shift;
  my $result = $self->edit_vote($lookfor);
  unless(defined($result)) {
      $result = $self->add_vote;
      $result->{ref} = $lookfor;
  }
  return $result;
}

sub methods {
  return qw(schulze rp); # whattelse?
}

sub default_method {
  return "schulze";
}

sub parse {
  my $self = shift;
  return unless (-e $self->filename);
  my $FH;
  open $FH, "<", $self->filename;
  my @lines = <$FH>;
  close $FH;
  my $firstline = shift @lines;
  chomp $firstline;
  $self->{method} = (@{[$firstline =~ /-m ([^ ]+)/]}[0]);
  my @conds = @{[split / /, @{[($firstline =~ /-cands ([^-]+)/)]}[0]]};
  $self->{cands} = \@conds;
  $self->{descriptions} = {};
  $self->{description} = "";
  my @votes = ();
  foreach(@lines) {
    chomp $_;
    next if($_ =~ /^#?\s*$/);
    if(my $res = @{[($_ =~ /^#(.*)$/)]}[0]) {
      if(my @data = ($res =~ /^MAGIC_([A-Z]):(.+)/)) {
        $self->{descriptions}->{$data[0]} = $data[1];
      } else {
        $self->{description} .= $res . "\n";
      }
    } else {
      push @votes, Vote::Individual->parse($_, $self->{cands});
    }
  }
  $self->{votes} = \@votes;
}

sub filename {
  my $self = shift;
  return $self->{fname};
}

sub unlink {
    my $self = shift;
    unlink $self->{fname};
}

sub save {
  my $self = shift;
  my $FH;
  open $FH, ">", $self->filename;
  print $FH "-m " . $self->{method} . " -cands " . join(" ", @{$self->{cands}}) . "\n";
  my $desc = "" . $self->{description};
  $desc =~ s/^/#/g;
  $desc =~ s/\n/\n#/g;
  $desc =~ s/^#\s+$//g;
  print $FH $desc . "\n";
  foreach(@{$self->{cands}}) {
    if(defined($self->{descriptions}->{$_})) {
      print $FH "#MAGIC_" . $_ . ":" . $self->{descriptions}->{$_} . "\n";
    }
  }
  foreach(@{$self ->{votes}}) {
    print $FH $_->to_line if(ref($_) eq "Vote::Individual");
  }
  close $FH;
}

sub do_report {
  my $self = shift;
  $self->save;
  my $file = $self->filename;
  my $result = `$engine < $file`;
  return $result;
}

sub format_table {
    my $results = "";
    my $text = shift;
	      my @rows = split /\n/, $text;
	      my $row = 1;
	      $results .= "<table><tbody>";
	      foreach my $r(@rows) {
		  my $col = 1;
		  $results .= "<tr>";
		  my @cols = split(/\s+/, $r);
		  foreach my $c(@cols) {
		      my $color = (($row == 1 && $col == 1) ? "" : (((($col + ($row % 2))  % 2) == 0) ? "#ffcccc" : "#99ff99"));
		      $results .= "<td bgcolor='" . $color . "'>" . $c . "</td>";
		      $col ++;
		  }
		  $results .= "</tr>";
		  $row ++;
	      }
	      $results .= "</tbody></table>";
    return $results;
}

sub report {
  my $self = shift;
  my $str = "";
  my $report = $self->do_report;
  my @lines = split /\n/, $report;
  my $seen_vote = 0;
  my $number_votes = 0;
  my $results = "";
  my $text = "";
  my $in_table = 0;
  foreach(@lines) {
    if($seen_vote == 0) {
      if($_ =~ /VOTES/) {
        $number_votes = @{[$_ =~ /(\d+)/]}[0];
	$seen_vote = 1;
      }
    } else {
	if($in_table == 0) {
	    if($_ =~ /^\s+[A-Z]+/) {
		$text =~ s/\n/ /g;
		$results .= "<h2>" . $text . "</h2>";
		$text = $_. "\n";
		$in_table = 1;
	    } else {
		          if($_ =~ /^\s*$/ && length($text) > 0) {
		$results .= "<h2>Final Ranking</h2>" . $text;
		$text = "";
	    } else {
		$text .= $_ . "\n";
	    }
	    }
        } else {
          if($_ =~ /^\s*$/) {
	      $results .= format_table($text);
#	      $results .= "<pre>" . $text . "</pre>";
	      $text = "";
	      $in_table = 0;
          } else {
	      $text .= $_ . "\n";
	  }
        }
    }
  }
  if(length($text) > 0) {
      if($in_table == 0) {
		$text =~ s/\n/ /g;
		$results .= "<h2>Final Ranking</h2>" . $text;
	    } else {
		$results .= format_table($text);
	    }
  }
  $str .= "<h1>" . MyUtils::hoomanize($self->{name}) . "</h1>";
  $str .= "<p><b>Votes:</b> " . $number_votes . "</p>";
  my $desc = "" . $self->{description};
  $desc =~ s/\n/<br \/>/g;
  $str .= "<p>" . $desc . "</p>";
  $str .= "<h2>Options</h2>";
  $str .= "<table>";
  foreach(@{$self->{cands}}) {
      $str .= "<tr><th>" . $_ . ":</th><td>" . $self->{descriptions}->{$_} . "</td></tr>";
  }
  $str .= "</table>";
  $str .= $results;
  $str .= "ERROR: failed to count correctly\n" if($number_votes != $self->number_votes);
#  $str .= "<h2>Raw Results</h2><pre>\n" . $report . "</pre>\n"; # formatted HTML now
  return $str;
}

package Vote::Individual;

sub new {
  my $class = shift;
  my $cands = shift;

  my $self = {};
  $self->{ref} = "";
  $self->{cands} = $cands;
  foreach(@$cands) {
    $self->{$_} = "";
  }

  bless $self, $class;

  return $self;
}

sub apply_options {
  my $self = shift;
  my $opts =  shift;
  foreach(keys %$opts) {
    $self->{$_} = $opts->{$_};
  }
}

sub updated {
    my $self = shift;
  $self->{line} = $self->_to_line; # update it
}

sub parse {
  my $class = shift;
  my $line = shift;
  my $cands = shift;

  my $self = {};


  bless $self, $class;

  $self->{line} = $line;
  $self->{cands} = $cands;

  $self->_parse;

  return $self;
}

sub _parse {
  my $self = shift;

  my @lineparts = @{[($self->{line} =~ /^([^#]+)(?:#(.+))?/)]};

  if(defined($lineparts[1])) {
    $lineparts[1] =~ s/^\s+//;
    $self->{ref} = $lineparts[1];
  }

  my @list = grep !/ /, split //, $lineparts[0];
  my $i = 0;
  my $next_i = 1;
  my $mode = ">";
  foreach(@list) {
    if($_ =~ /[=>]/) {
      $mode = $_;
    } else {
      if($mode eq ">") {
        $i = $next_i;
        $next_i++;
      } else {
        $mode = ">";
        $next_i++; # remove this in order to not incriment if you don't want to skip numbers after ties. it doesn't really matter probably.
      }
      $self->{$_} = $i;
    }
  };
  # parse $self->{line} into $self->{ref,A,B,etc};
}

sub to_line {
  my $self = shift;
  return $self->{line} . "\n";
}

sub _to_line {
  my $self = shift;
  my $myline = "";
  my $lastfound = 0;
  my $max = scalar(@{$self->{cands}});
  foreach my $char(@{$self->{cands}}) {
      $max = $self->{$char} if ($self->{$char} > $max);
  }
  foreach my $num(1 .. $max) {
    foreach my $char(@{$self->{cands}}) {
      if(defined($self->{$char}) && $self->{$char} eq $num) {
        $myline .= "= " if($lastfound eq $num);
        $myline .= $char . " ";
        $lastfound = $num;
      }
    }
  }
  my $com = "";
  if(defined($self->{ref})) {
    $com = " # " . $self->{ref};
  }
  return $myline . $com;
}

package main;

use CGI::FormBuilder;

use strict;
use warnings;

sub quickform {
    my ($fname, $text, $mode, $item_name, $header) = @_;
    $header = $header || 0;
    my @list = ('mode');
    if(defined($item_name)) {
	push @list, 'name';
    }
    my $ticket_form = CGI::FormBuilder->new(fields => [], method   => 'post', submit => $text, name => $fname, keepextras => \@list, header => $header, stylesheet => $MyUtils::css);
    if(defined($mode)) {
	$ticket_form->cgi_param('mode', $mode);
    }
    if(defined($item_name)) {
	$ticket_form->cgi_param('name', $item_name);
    }
    return $ticket_form;
}

use File::Temp qw/tempfile/;
use File::Basename qw(basename);

my $t = quickform("testform", "whee");
my $mode = $t->cgi_param('mode') || "index";
my $thing_name = $t->cgi_param('name');

do_main($mode);

sub header_for_main {
    print quickform("back", "Main Page", "index", undef, 1)->render;
}

sub show {
    my $v = shift;
    header_for_main();
#    print quickform("add_vote", "Add Vote", "add", $v->{name})->render;
    print quickform("show_ballots", "Show Ballots", "ballots", $v->{name})->render;
    print quickform("edit_info", "Options", "edit", $v->{name})->render;
    print quickform("delete", "Delete Completely", "delete", $v->{name})->render;
    print $v->report;
}

use CGI;

sub header_for_empty {
    print CGI::header();
    my $s = $MyUtils::css;
    print "<link href=\"$s\" rel=\"stylesheet\" type=\"text/css\" />\n";
}

sub do_main {
    my $mode = shift;
    if($mode eq "index") {
	my @fields = qw(name candidates);
	my $form = CGI::FormBuilder->new(name => "new_one", fields => \@fields, header => 1, method   => 'post', required => 'ALL', keepextras => ['mode', 'step'], validate => {candidates => 'NUM'}, title => 'Create New Vote', labels => {candidates => '# of Candidates'}, stylesheet => $MyUtils::css);
	if($form->submitted && $form->validate) {
	    my $step = $form->cgi_param('step');
	    my @more = qw(description);
	    my @required = ();
	    my $cands = $form->cgi_param('candidates');
	    foreach(1 .. $cands) {
		my $o = 'option_' . chr(64 + $_);
		push @more, $o;
		push @required, $o;
	    }
	    if($step eq 'one') {
		my $form = CGI::FormBuilder->new(name => "new_one", fields => \@more, header => 1, method   => 'post', required => \@required, keepextras => ['name', 'mode', 'candidates', 'step'], title => 'Create New Vote for ' . $form->field('name'), stylesheet => $MyUtils::css);
		$form->cgi_param('step', 'two');
		$form->field(name => 'description', type => 'textarea');
		print $form->render;
	    } else { # step two submitting
		my $form = CGI::FormBuilder->new(name => "new_one", fields => \@more, header => 1, method   => 'post', required => \@required, keepextras => ['name', 'mode', 'candidates', 'step'], title => 'Create New Vote for ' . $form->field('name'), stylesheet => $MyUtils::css);
		my $name = $form->cgi_param('name');
		my $v = Vote->new(MyUtils::dehoomanize($name), $cands);
		my $desc = $form->field('description');

		$v->{description} = $desc;

		foreach(1 .. $cands) {
		    my $c = chr(64 + $_);
		    my $opt = $form->field('option_' . $c);
		    $v->{descriptions}->{$c} = $opt;
		}

		show($v);
	    }
	} else {
	    $form->cgi_param('step', 'one');
	    print $form->render;
	    print "<h3>Past Votes</h3>";
	    my @votes = Vote->list_votes;
	    foreach my $vote(@votes) {
		print quickform("vote_" . $vote, "View " . MyUtils::hoomanize($vote), "view", $vote)->render;
	    }
	}
#    } elsif($mode eq "add") {
#	my $vote = Vote->load(basename($thing_name));
#	my @opts = qw(ref);
#	my $h = {};
#	my $l = {};
#	$l->{ref} = 'Reference ID';
#	my @list = @{$vote->{cands}};
#
#	$h->{'ref'} = 'NUM'; # should ref be validated too?
#	foreach my $c(@list) {
#	    my $o = 'option_' . $c;
#	    my $desc = $vote->{descriptions}->{$c} || "";
#	    push @opts, $o;
#	    $h->{$o} = 'NUM';
#	    $l->{$o} = $c . ': ' . $desc;
#	}
#	my $form = CGI::FormBuilder->new(name => "new_one", fields => \@opts, header => 1, method   => 'post', required => ['ref'], keepextras => ['mode', 'name'], validate => $h, title => 'Add Vote', labels => $l, title => 'Add Vote', stylesheet => $MyUtils::css);
#	if($form->submitted && $form->validate) {
#	    my $this = $vote->add_vote;
#	    $this->{ref} = $form->field('ref');
#	    foreach my $c(@list) {
#		$this->{$c} = $form->field('option_' . $c);
#	    }
#	    $this->updated;
#	    show($vote);
#	} else {
#	    print $form->render;
#	}
    } elsif($mode eq "edit") {
	my $vote = Vote->load(basename($thing_name));
	my @more = qw(description number_candidates);
	my @required = qw(number_candidates);
	my @cands = @{$vote->{cands}};
	foreach my $c(@cands) {
	    my $o = 'option_' . $c;
	    push @more, $o;
	    push @required, $o;
	}
	my $form = CGI::FormBuilder->new(name => "new_one", fields => \@more, header => 1, method   => 'post', required => \@required, keepextras => ['mode', 'name'], title => 'Editing vote metadata for ' . MyUtils::hoomanize($vote->{name}), stylesheet => $MyUtils::css);
	$form->field(name => 'description', type => 'textarea');
	$form->field(name => 'number_candidates', validate => 'NUM');
	my @opts = Vote->methods;
	$form->field(name => 'method', type => 'select',selectname => 0, options => \@opts);
	if($form->submitted && $form->validate) {
		my $desc = $form->field('description');

		$vote->{description} = $desc;

		$vote->{method} = $form->field('method');

		my $cand_num = $form->field('number_candidates');
		$vote->update_cands($cand_num) if($cand_num != $vote->number_cands);

		foreach my $c(@cands) {
		    my $opt = $form->field('option_' . $c);
		    $vote->{descriptions}->{$c} = $opt;
		}

	    show($vote);
	} else {
	    if(!$form->submitted) {
		$form->field(name => 'description', value => $vote->{description});
		$form->field(name => 'method', value => $vote->{method});
		$form->field(name => 'number_candidates', value => $vote->number_cands);
		foreach my $c(@cands) {
		    my $o = 'option_' . $c;
		    $form->field(name => $o, value => $vote->{descriptions}->{$c});
		}
	    }
	    print $form->render;
	}
    } elsif($mode eq "delete") { # mode is view
	Vote->load(basename($thing_name))->unlink;
	do_main("index");
    } elsif($mode eq "ballots") {
	my $vote = Vote->load(basename($thing_name));
	my $form = CGI::FormBuilder->new(name => "ballots", fields => ['how_many', 'starting_number'], header => 1, method   => 'post', required => 'ALL', keepextras => ['mode', 'name'], title => 'Print or edit ballots for ' . MyUtils::hoomanize($vote->{name}), stylesheet => $MyUtils::css);
	my $tabindex = 1;
	if($form->submitted && $form->validate) {
	    my $many = $form->field('how_many');
	    my $start = $form->field('starting_number');
	    my $end = $start + $many - 1;
	    header_for_empty();
	    my $count = 0;
	    my %hash = ();
	    $hash{"left"} = "";
	    $hash{"right"} = "";
	    foreach my $num($start .. $end) {
		my $div = (($count % 2) == 0) ? "left" : "right";
		$count += 1;
		my $str = "<fieldset>";
		$str .= "<h1>" . $vote->{name} . "</h1>";
		$str .= "Reference ID#" . $num;
		$str .= "<p>" . $vote->{description} . "</p>";
		my $b = $vote->add_or_edit_vote($num);
		foreach my $cand(@{$vote->{cands}}) {
		    $str .= "<input tabindex=\"" . $tabindex . "\" name=\"" . "vote_" . $num . "_" . $cand . "\" size=\"1\" value=\"" . ($b->{$cand} || "") . "\"/> <b>" . $cand . ":</b> " . $vote->{descriptions}->{$cand} . "<br />";
		    $tabindex++;
		}
		$str .= "</fieldset>";
		$hash{$div} .= $str;
	    }
	    print '<form action="voteengine.cgi" class="fb_form" id="save_ballots" method="post" name="save_ballots">' . '<input id="_submitted_save_ballots" name="_submitted_save_ballots" type="hidden" value="1" />' . '<input id="mode" name="mode" type="hidden" value="save_ballots" />' . '<input id="name" name="name" type="hidden" value="' . $vote->{name} . '" />' . '<input id="start" name="start" type="hidden" value="' . $start . '" />' . '<input id="end" name="end" type="hidden" value="' . $end . '" />';
	    print '<div class="noprint" style="clear: left;">' . '<h1>Printing or Editing Ballots</h1><input class="fb_button" id="save_ballots_submit" name="_submit" type="submit" tabindex=\"" . $tabindex . "\" value="Save" />' . '</div>';
	    print "<div class=\"left\">" . $hash{"left"} . "</div>";
	    print "<div class=\"right\">" . $hash{"right"} . "</div>";
	    print '</form>';
	} else {
	    $form->field(name => 'starting_number', value => '1');
	    print $form->render;
	}
    } elsif($mode eq "save_ballots") {
	my $form = CGI::FormBuilder->new(name => "save_ballots", header => 1, method   => 'post', stylesheet => $MyUtils::css);
	my $vote = Vote->load(basename($thing_name));;
	my @cands = @{$vote->{cands}};
	my $start = $form->cgi_param("start");
	my $end = $form->cgi_param("end");
	foreach my $num($start .. $end) {
	    my $b = $vote->add_or_edit_vote($num);
	    my $changed = 0;
	    foreach my $cand(@cands) {
		my $val = $form->cgi_param("vote_" . $num . "_" . $cand);
		if(defined($val)) {
		    if($val ne "") {
			$changed += 1;
		    }
		    $b->{$cand} = $val;
		}
	    }
	    if($changed > 0) {
		$b->updated;
	    } else {
#	    if(!defined($b->{line})) {
		$vote->remove_vote($num);
	    }
	}
	show($vote);
    } else {
	show(Vote->load(basename($thing_name)));
    }
}
