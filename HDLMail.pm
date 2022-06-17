package HDLMail;

use strict;
my $hasb64 = 1;
$hasb64 = 0 unless eval "require MIME::Base64";

my $mailer;
my $smtphost;
my $usesmtp;

my $CRLF    = "\015\012";


# ======================================================================= encode

sub encode {
  return $_[0] if $_[0] !~ /[^a-zA-Z0-9 ()[\]_!\/\\{}"';:?<>@#\$%&*\n\r.,-]/;
  return "=?ISO-8859-1?B?".base64($_[0], "")."?=" if !$_[1];
  my $adr = $_[0];
  $adr =~ s/"[^"]*"//;
  $adr =~ s/^[^<]*<//g;
  $adr =~ s/>[^>]*$//g;
  $adr =~ s/^\s+//;
  $adr =~ s/\s+$//;
  my $name = $_[0];
  $name =~ s/<[^>]*>//g;
  $name =~ s/"//g;
  $name =~ s/[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+//g;
  $name =~ s/^\s+//;
  $name =~ s/\s+$//;
  $name =~ s/\s\s+/ /;
  $name = "=?ISO-8859-1?B?".base64($name, "")."?=" if $name ne undef;
  $name =~ s/\r?\n\r?\s+/ /g;
  my $str;
  if ($name ne undef) {
    $str = "\"$name\" ";
  }
  $str .= "<$adr>";
  return $str;
}
# ========================================================================= smtp

sub smtp {
  if ($usesmtp eq undef) {
    if ($mailer ne undef && -x $mailer) {
      $usesmtp = 0;
    } else {
      $usesmtp = 1;
      unless (eval "require Net::SMTP") { $usesmtp = 0; }
    }
  }
  return $usesmtp;
}
# ===================================================================== sendmail

sub sendmail {
  $mailer = $_[0]->{mailer};
  $smtphost = $_[0]->{smtp};
  my $contenttype = "MIME-Version: 1.0\nContent-Type: text/plain; charset=\"ISO-8859-1\"\nContent-Transfer-Encoding: quoted-printable";
  if (!smtp()) {
    return 0 if !open(MAIL, "|$mailer -t");
    my $bcc = "Bcc: ".$_[0]->{bcc}."\n" if $_[0]->{bcc} ne undef;
    print MAIL "To: ".$_[0]->{to}."\nFrom: ".encode($_[0]->{from}, 1)."\n".$bcc.
               "Subject: ".encode($_[0]->{subject}, 0).
               "\n$contenttype\n\n".
               quoteit($_[0]->{msg})."\n\n";
    close MAIL;
  } else {
    my $to = $_[0]->{to};
    $to =~ s/"[^"]*"//;
    $to =~ s/^[^<]*<//g;
    $to =~ s/>[^>]*$//g;
    $to =~ s/^\s+//;
    $to =~ s/\s+$//;
    my $from = $_[0]->{from};
    $from =~ s/"[^"]*"//;
    $from =~ s/^[^<]*<//g;
    $from =~ s/>[^>]*$//g;
    $from =~ s/^\s+//;
    $from =~ s/\s+$//;
    my $s = Net::SMTP->new($smtphost);
    if ($s ne undef) {
      $s->mail($from);
      $s->to($to);
      $s->data();
      $s->datasend("To: ".$_[0]->{to}."\n");
      $s->datasend("From: ".encode($_[0]->{from}, 1)."\n");
      $s->datasend("Subject: ".encode($_[0]->{subject}, 0).
                   "\n$contenttype\n\n");
      $s->datasend(quoteit($_[0]->{msg}));
      $s->datasend("\n\n");
      $s->dataend();
      $s->quit();
    }
  }
  return 1;
}
# ====================================================================== quoteit

sub quoteit {
  my $in = shift;
  my $out;
  local $_;
  $in =~ s/\015?\012/\n/g;
  while (1) {
    $in =~ s/^(.*?(?:(?:\n)|\Z))//m;
    $_ = $1;
    (defined and length) or last;
    s/([^ \t\n!-<>-~])/sprintf("=%02X", ord($1))/eg;
    s/([ \t]+)$/join('', map { sprintf("=%02X", ord($_)) } split('', $1))/egm;
    my $brokenlines = "";
    $brokenlines .= "$1=\n"
    while s/(.*?^[^\n]{73} (?:
         [^=\n]{2} (?! [^=\n]{0,1} $)
         |[^=\n]    (?! [^=\n]{0,2} $)
         |          (?! [^=\n]{0,3} $)
         ))//xsm;
    $_ = "$brokenlines$_";
    if (length($_) < 74) {
      s/^\.$/=2E/g;
      s/^From /=46rom /g;
    }
    s/\015?\012/$CRLF/g;
    $out .= $_;
    (defined($in) and length($in)) or last;
  }
  return $out;
}
# ======================================================================= base64

sub base64 {
  my $in = $_[0];
  my $out;
  my $eol = $_[1];
  $eol = "\n" unless defined $eol;
  while (1) {
    my ($buf, $b64);
    last unless length $in;
    $buf = substr($in, 0, 45);
    substr($in, 0, 45) = '';
    if ($hasb64) {
      $b64 = MIME::Base64::encode_base64($buf, $eol);
    } else {
      $b64 = _b64($buf, $eol);
    }
    $b64 =~ s/\015?\012/$CRLF/g;
    $b64 .= $CRLF if length $eol && $b64 !~ /$CRLF\Z/;
    $out .= $b64;
  }
  return $out;
}
# ========================================================================= _b64
sub _b64 {
  my $out = "";
  my $eol = $_[1];
  $eol = "\n" unless defined $eol;
  pos($_[0]) = 0;
  while ($_[0] =~ /(.{1,45})/gs) {
    $out .= substr(pack('u', $1), 1);
    chop($out);
  }
  $out =~ tr|` -_|AA-Za-z0-9+/|;
  my $padding = (3 - length($_[0]) % 3) % 3;
  $out =~ s/.{$padding}$/'=' x $padding/e if $padding;
  if (length $eol) {
    $out =~ s/(.{1,76})/$1$eol/g;
  }
  return $out;
}


1;