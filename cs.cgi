#!C:/wamp/bin/Perl64/bin/perl.exe
#

use strict;

# Data directory - the directory to store ticket database. Default is ./data.
# IMPORTANT: some servers disable writing to scripts directory and default
# settings for $datadir may result in Internal server error
my $datadir = "data";

# Your sendmail program. If you are on Windows server, leave it blank and use
# $smtphost variable below
my $mailer = "";

# SMTP host address. The value will be ignored is $mailer is non empty and
# points to executable file
my $smtphost = 'br01.oxynet.com.br';

# Your help desk email address - all notifications will be send from this address
my $helpdeskaddress = "helpsesk\@your-company-domain.com";

# Company Name
my $companyname = "Câmara Municipal de Castro";

# Home page url
my $companyurl = "http://camaracastro.pr.gov.br";

# Help desk password - in order to login to help desk an operator must provide
# his/her email address and this password
my $helpdeskpassword = 'teste';

# Notification email address - Every time a visitor posts new inquiry
# the help desk will send a notification to this address. It is supposed
# to be a broadcast address.
my $notifyaddress = $helpdeskaddress;

# ==== NOTHING TO EDIT BELOW THIS LINE. PLS DO NOT CROSS IF NOT SURE ===========

require HDLMail;

my $version = '0.99';
my $ticketdb;
my @tickfields = ('id', 'email', 'name', 'subject', 'open', 'taken', 'oper');
my @rclr = ('#F0F0E1', '#E8E8CF');
my @rcls = ('orow', 'erow');

BEGIN {
  if ($^O eq 'MSWin32') {
    eval "use FindBin";
    eval "use lib $FindBin::Bin";
    chdir($FindBin::Bin);
  }
}

if ($ENV{HTTP_HOST} eq undef) {
  mailbox();
  exit;
}

print "Content-type: text/html\n\n";
use CGI;
my $query = new CGI;
my $cmd = $query->param('cmd');
header();
login() if $cmd eq 'login';
if ($cmd eq 'login') {
  footer();
  exit;
}
$cmd = 'newticket' if $cmd eq undef;
if ($cmd eq 'newticket') {
  newticket();
} elsif ($query->param('pwd') eq undef || $query->param('pwd') ne $helpdeskpassword) {
  login();
  footer();
  exit;
}
if ($cmd eq 'helpdesk') {
  helpdesk();
} elsif ($cmd eq 'ticket') {
  ticket();
} elsif ($cmd eq 'claim') {
  claim();
} elsif ($cmd eq 'history') {
  history();
}
footer();
exit;

# ====================================================================== mailbox

sub mailbox {
}
# ======================================================================== login

sub login {
  my $error;
  if ($query->param('do')) {
    if (cleanit($query, ('userid')) eq undef) {
      $error = "Campo obrigatorio: Email";
    } elsif ($query->param('userid') !~ /^[0-9A-Za-z._-]+@[0-9A-Za-z_-]+\.[0-9A-Za-z._-]+$/) {
      $error = "Campo invalido: Email";
    } elsif (cleanit($query, 'passwd') eq undef) {
      $error = "Campo obrigatorio: password";
    } elsif ($query->param('passwd') ne $helpdeskpassword) {
      $error = "Campo invalido: password";
    } else {
      $cmd = 'helpdesk';
      $query->param(-name => 'pwd', -value => $helpdeskpassword);
      $query->param(-name => 'do', -value => '');
      return;
    }
  }
  $error = $_[0] if $error eq undef;
  $error .= "<br><br>" if $error ne undef;
  my $userid = $query->param('userid');
  $userid =~ s/"/&quot;/g;
  print "<font color=red><b>$error</b></font><form method=post action=\"$ENV{SCRIPT_NAME}\">\n".
        "<input type=hidden name=cmd value=login>\n<input type=hidden name=do value=1>\n";
  print "<table cellspacing=5><tr><td align=right><b>Endereco Email</b></td>".
        "<td align=left><input type=text size=20 name=userid value=\"$userid\"></td></tr>\n".
        "<tr><td align=right><b>Password</b></td>\n".
        "<td align=left><input type=password name=passwd size=20></td></tr>\n".
        "<tr><td colspan=2 align=right><input type=submit value=Login></td></tr></form></table>\n";
}
# ==================================================================== newticket

sub newticket {
  my %data;
  if ($query->param('do')) {
    my $ticket;
    $ticket->{name} = cleanit($query, 'name');
    $ticket->{email} = cleanit($query, 'email');
    $ticket->{subject} = cleanit($query, 'subject');
    $ticket->{message} = cleanit($query, 'message');
    my $error;
    if ($ticket->{name} eq undef) {
      $error = "Campo obrigatorio: nome<br>";
    }
    $ticket->{name} =~ s/\b(\w)/uc($1)/eg;
    if ($ticket->{email} eq undef) {
      $error .= "Campo obrigatorio: email<br>\n";
    } elsif ($ticket->{email} !~ /^[0-9A-Za-z._-]+@[0-9A-Za-z_-]+\.[0-9A-Za-z._-]+$/) {
      $error .= "Campo invalido: email<br>";
    }
    if ($ticket->{subject} eq undef) {
      $error .= "Campo obrigatorio: Assunto<br>";
    }
    if ($error ne undef) {
      $error =~ s/<br>$//;
      $data{ERROR_MESSAGE} = $error;
    } else {
      my $custom;
      my @inputs = sort $query->param();
      foreach my $input (@inputs) {
        next if $input !~ /^x/;
        next if $query->param($input) eq undef;
        my $val = $query->param($input);
        $input =~ s/^x//;
        $custom .= "$input: $val\n";
      }
      $custom .= "\n" if $custom ne undef;
      $ticket->{message} = $custom . $ticket->{message};
      $data{ERROR_MESSAGE} = saveticket($ticket);
      if ($data{ERROR_MESSAGE} eq undef) {
        confirm($ticket);
        return;
      }
    }
  }
  my $tmpl = template($query->param('form'));
  foreach my $key ($query->param) {
    $data{"INPUT_".$key} = $query->param($key);
    if ($key ne 'message') {
      $data{"INPUT_".$key} =~ s/"/&quot;/g;
    } else {
      $data{"INPUT_".$key} =~ s/</&lt;/g;
    }
  }
  foreach my $key (keys %ENV) {
    $data{"ENV_".$key} = $ENV{$key};
  }
  $tmpl =~ s/\(%\s*([a-zA-Z0-9_]+)\s*%\)/$data{$1}/g;
  print $tmpl;
}
# ===================================================================== helpdesk

sub helpdesk {
  my $error = loaddb();
  if ($error ne undef) {
    print "<font color=red><b>$error</b></font><br><br>\n";
    return;
  }
  my @list = grep {$ticketdb->{$_}->{oper} eq undef} keys %{$ticketdb};
  @list = sort {$ticketdb->{$b}->{open} <=> $ticketdb->{$a}->{open}} @list;
  print "<br><table cellpadding=0 cellspacing=0 width=650>\n<tr><td align=center class=trow><b>id</b></td><td class=trow align=center><b>subject</b></td>".
        "<td class=trow align=center><b>email</b></td><td class=trow align=center><b>posted</b></td></tr>\n";
  my $i = 0;
  my $j = 0;
  if (@list < 1) {
    print "<tr><td colspan=4 align=center><b>Sem chamados pendentes</b></td></tr>\n";
  }
  foreach my $id (@list) {
    my $clr = $rclr[$i];
    my $cl = $rcls[$i];
    ++$i;
    ++$j;
    $i = 0 if $i > 1;

    my $subject = $ticketdb->{$id}->{subject};
    my $dots = '...';
    $subject =~ s/\b([^\s]{20,20})([^\s])*/$1.$dots/ge;
    $subject =~ /^(.{1,30})(.*)/;
    $subject = $1;
    $subject .= '...' if $2 ne undef;
    $subject =~ s/</&lt;/g;
    $subject = "<a href=\"$ENV{SCRIPT_NAME}?cmd=ticket&tid=$id&pwd=$helpdeskpassword&userid=".$query->param('userid')."\">$subject</a>";
    print "<tr bgcolor=\"$clr\" onmouseover=\"rowhl($j, 1);\" onmouseout=\"rowhl($j, 0);\" id=\"tr$j\">\n";
    print "<td valign=top class=$cl align=right>$id</td><td valign=top class=$cl align=left>$subject</td>".
          "<td valign=top class=$cl align=right><a href=\"mailto:".$ticketdb->{$id}->{email}."\">".$ticketdb->{$id}->{email}."</a></td>\n".
          "<td valign=top class=$cl align=right>".formatdate($ticketdb->{$id}->{open})."</td></tr>\n";
  }
  print "</table>\n\n";
}
# ======================================================================= ticket

sub ticket {
  my ($tid, $subject, $pdate, $name, $email, $operdate, $message);
  $tid = cleanit($query, 'tid');
  loaddb();
  my $ticket = $ticketdb->{$tid};
  $subject = $ticket->{subject};
  $subject =~ s/</&lt;/g;
  $pdate = formatdate($ticket->{open});
  $name = $ticket->{name};
  $name =~ s/</&lt;/g;
  $email = $ticket->{email};
  if ($ticket->{oper} ne undef) {
  } else {
    $operdate = 'not assigned';
  }
  if (open(MSG, "$datadir/$tid.cgi")) {
    my @buff = <MSG>;
    close MSG;
    $message = join('', @buff);
    $message =~ s/</&lt;/g;
    $message =~ s/\n/<br>/g;
  }
  my $pwd = $query->param('pwd');
  my $userid = $query->param('userid');
  my $claim =<<EOT;
<form method=post action=$ENV{SCRIPT_NAME}>
<input type=hidden name=cmd value=claim>
<input type=hidden name=tid value=$tid>
<input type=hidden name=pwd value=$pwd>
<input type=hidden name=userid value=$userid>
<tr><td colspan=2 align=right>
EOT
  if ($ticket->{oper} eq undef) {
    $claim .= "<input type=submit value=\"Claim ownership\">\n";
  }
  $claim .=<<EOT;
<input type=submit name=cancel value="Cancelar"></tr>
</form>
EOT

  print <<EOT;
<table width=650 cellpadding=5 cellspacing=0>
  <tr>
    <td align=left bgcolor="#CFDCE8">
      <table cellspacing=0 cellpadding=1>
        <tr>
          <td align=left><b>Ticket</b></td>
          <td align=left>&nbsp;&nbsp;$tid</td>
        </tr>
        <tr>
          <td align=left><b>Assunto</b></td>
          <td align=left>&nbsp;&nbsp;$subject</td>
        </tr>
        <tr>
          <td align=left><b>Aberto em</b></td>
          <td align=left>&nbsp;&nbsp;$pdate</td>
        </tr>
        <tr>
          <td align=left><b>Cliente</b></td>
          <td align=left>&nbsp;&nbsp;$name (<a href="mailto:$email">$email</a>)</td>
        </tr>
        <tr>
          <td align=left><b>Operador</b></td>
          <td align=left>&nbsp;&nbsp;$operdate</td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td height=2></td>
  </tr>
  <tr>
    <td align=left bgcolor="#F0F0E1">
    $message
    </td>
  </tr>
  $claim
</table>
EOT
}
# =================================================================== formatdate

sub formatdate {
  return "-" if !$_[0];
  my ($sec,$min,$hour,$mday,$mon,$year) = localtime($_[0]);
  my $date;
  $year += 1900; $year =~ s/^\d\d//;
  $mon++; $mon = "0$mon" if $mon < 10;
  $mday = "0$mday" if $mday < 10;
  $date = "$mon/$mday/$year ";
  $hour = "0$hour" if $hour < 10;
  $min = "0$min" if $min < 10;
  $date .= "$hour:$min";
  return $date;
}
# ======================================================================== claim

sub claim {
  if ($query->param('cancel') ne undef) {
    helpdesk();
    return;
  }
  my $tid = cleanit($query, 'tid');
  loaddb();
  my $ticket = $ticketdb->{$tid};
  if ($ticket->{oper} ne undef) {
    print "<br><b>Ticket is already assigned to <a href=\"mailto:".$ticket->{oper}.
          "\">".$ticket->{oper}."</a></b><br><br>\n";
  } else {
    $ticket->{oper} = $query->param('userid');
    $ticket->{taken} = time();
    updateticket($ticket);
    forwardticket($ticket);
    print "<br><b>Ticket assigned. A copy of the ticket was sent to ".$ticket->{oper}."</b><br><br>\n";
  }
  my $pwd = $query->param('pwd');
  my $userid = $query->param('userid');
  print <<EOT;
<form action="$ENV{SCRIPT_NAME}" method=post>
<input type=hidden name=cmd value=helpdesk>
<input type=hidden name=pwd value="$pwd">
<input type=hidden name=userid value="$userid">
<input type=submit value=Continue>
</form>
EOT
}
# ================================================================ forwardticket

sub forwardticket {
  my $ticket = shift;
  if (open(MSG, "$datadir/".$ticket->{id}.".cgi")) {
    my @buff = <MSG>;
    close MSG;
    my $message = join('', @buff);
    HDLMail::sendmail(
    {
       mailer => $mailer,
       smtp => $smtphost,
       to => $ticket->{oper},
       from => "\"".$ticket->{name}."\" <".$ticket->{email}.">",
       subject => "Ticket [".$ticket->{id}."], ".$ticket->{subject},
       msg => "Posted: ".localtime($ticket->{open})."\n\n$message\n"
    }
  );
  }
}
# ====================================================================== history

sub history {
}
# ======================================================================= header

sub header {
  my $oper = $query->param('userid');
  my $pwd = $query->param('pwd');
  my ($helpdesk, $login);
  if ($oper ne undef && $pwd eq $helpdeskpassword) {
    $helpdesk = "<a href=\"$ENV{SCRIPT_NAME}?cmd=helpdesk&userid=$oper&pwd=$pwd\">helpdesk</a>";
    $login = "<a href=\"$ENV{SCRIPT_NAME}?cmd=newticket\">logout</a>";
    $oper = "<font color=\"#AAAAAA\"><b>Logged as $oper</b></font>";
  } else {
    $helpdesk = "<a href=\"$ENV{SCRIPT_NAME}?cmd=newticket\">contact us</a>";
    $login = "<a href=\"$ENV{SCRIPT_NAME}?cmd=login\">login</a>";
    $oper = "<b>Central de Suporte da $companyname</b>";
  }
  print <<EOT;
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN"
"http://www.w3.org/TR/REC-html40/loose.dtd">
<html>
<head>
<title>Help Desk Lite</title>
<style type="text/css">
body, td { font-family: Verdana, Helvetica, sans-serif; font-size: 10pt;}
A       { color : #2E3197; text-decoration : none; }
A:Hover { color : #C00; text-decoration : underline;}
.sm {font-size: 8pt;}
.tiny {font-size: 4pt;}
.heading {font-size: 13pt;font-weight: 700; color: #2E3197;}
.lbl { font-size: 9pt; font-weight: 700;}
td.error  {
  background-color: #FFC;
  padding-right: 5pt;
  padding-left: 5pt;
  padding-top: 3pt;
  padding-bottom: 3pt;
  border-width:1px;
  border-style:solid;
  border-color: #996;
  font-weight: 700;
  color: #F00;
}
td.trow  {
  padding-right: 2pt;
  padding-left: 2pt;
  border-style:solid;
  border-bottom-width:2px;
  border-right-width: 0px;
  border-left-width:1px;
  border-top-width:0;
  border-color: #FFF;
  background-color: #CCC;
  text-align: center;
  font-size : 8pt;
  font-weight: 700;
}
td.orow  {
  padding-right: 4pt;
  padding-left: 4pt;
  padding-top: 2pt;
  padding-bottom: 1pt;
  border-width:1px;
  border-style:solid;
  border-top-width:0;
  border-bottom-width:0;
  border-right-width:0;
  font-size : 8pt;
  border-color: #FFF;
}
td.erow  {
  padding-right: 4pt;
  padding-left: 4pt;
  padding-top: 2pt;
  padding-bottom: 1pt;
  border-width:1px;
  border-style:solid;
  border-top-width:0;
  border-bottom-width:0;
  border-right-width:0;
  font-size : 8pt;
  border-color: #FFF;
}
td.omsg  {
  background-color: #E8E8CF;
  padding-right: 3pt;
  padding-left: 3pt;
  padding-top: 2pt;
  padding-bottom: 2pt;
  border-width:1px;
  border-style:solid;
  border-color: #FFF;
}
td.cmsg  {
  background-color: #E8DCCF;
  padding-right: 3pt;
  padding-left: 3pt;
  padding-top: 2pt;
  padding-bottom: 2pt;
  border-width:1px;
  border-style:solid;
  border-color: #FFF;
}
</style>
<script language="JavaScript"><!--
function rowhl(id, inrow) {
  var row = document.getElementById('tr'+id);
  var odd = id % 2;
  var c = (odd) ? '#F0F0E1' : '#E8E8CF';
  row.style.backgroundColor = (inrow) ? '#FFFFD9' : c;
}
//--></script>
</head>
<body>
<center>
<br>
<table width=650 cellpadding=0 cellspacing=0>
  <tr>
    <td align=left><span class=sm>$oper</span></td>
    <td align=right class=sm>
        <a href="$companyurl">home</a> |
        $helpdesk |
        $login
    </td>
  </tr>
</table>
EOT
}
# ======================================================================= footer

sub footer {
  print <<EOT;
<table width=650 cellpadding=0 cellspacing=0>
  <tr>
    <td height=2></td>
  </tr>
  <tr>
    <td style="border-top-width:1px; border-style:solid; border-color: #CCC; border-bottom-width: 0px;
              border-left-width: 0px; border-right-width: 0px;" align=left>
      <span class=sm><font color="777777">Atualizado por <a href="http://www.camaracastro.pr.gov.br"
      style="color : #777;">Câmara Municipal de Castro</a> rev. 0.99</font></span>
    </td>
  </tr>
</table>
</center>
</body>
</html>
EOT
}
# ===================================================================== template

sub template {
  my $t;
  if ($_[0] ne undef) {
    my @parts = split(/\/|\\/, $_[0]);
    $t = pop @parts;
    $t .= '.html';
    $t = "$t";
    if (-f $t && open(TMPL, $t)) {
      my @buff = <TMPL>;
      close TMPL;
      my $tmpl = join('', @buff);
      return $tmpl;
    }
  }
  my $tmpl =<<EOT;
<font color=red><b>(%ERROR_MESSAGE%)</b></font><br><br class=tiny>
<table width=650 bgcolor="#CFDCE8">
  <form method=post action="(%ENV_SCRIPT_NAME%)" name=newticket>
  <input type=hidden name=cmd value=newticket>
  <input type=hidden name=do value=1>
  <input type=hidden name=pwd value="(%INPUT_pwd%)">
  <input type=hidden name=userid value="(%INPUT_userid%)">
  <input type=hidden name=form value="(%INPUT_form%)">
  <tr>
    <td colspan=2>&nbsp;</td>
  </tr>
  <tr>
    <td align=right><b>Name</b></td>
    <td align=left><input type=text name=name size=25 value="(%INPUT_name%)"></td>
  </tr>
  <tr>
    <td align=right><b>Email</b></td>
    <td align=left><input type=text name=email size=25 value="(%INPUT_email%)"></td>
  </tr>
  <tr>
    <td align=right><b>Subject</b></td>
    <td align=left><input type=text name=subject size=40 value="(%INPUT_subject%)"></td>
  </tr>
  <tr>
    <td align=right><b><br>Message</b></td>
    <td align=right>&nbsp;</td>
  </tr>
  <tr>
    <td align=center colspan=2><textarea cols=60 rows=12 wrap=virtual name=message>(%INPUT_message%)</textarea>
    <br><br class=tiny>
    <input type=submit value="Send your inquiry">
    </td>
    </form>
  </tr>
  <tr>
    <td colspan=2>&nbsp;</td>
  </tr>
</table>
EOT
  return $tmpl;
}
# =================================================================== saveticket

sub saveticket {
  my $ticket = shift;
  my $tm = time();
  my $message .= $ticket->{message}."\n";
  return addmsg($message, $ticket, $tm);
}
# ======================================================================= addmsg

sub addmsg {
  my ($message, $ticket, $tm) = @_;
  my $from = $ticket->{email};
  my $name = $ticket->{name};
  my $subject = $ticket->{subject};
  if (! -e $datadir) {
    if (!mkdir($datadir, 0777)) {
      return "Erro ao criar diretorio $datadir";
    }
  }
  my $cfn = "$datadir/counter.cgi";
  if (! -e $cfn) {
    if (open(CNT, ">$cfn")) {
      eval "flock(CNT, 2)";
      print CNT "0\n";
      close CNT;
      umask(0000);
      chmod(0766, $cfn);
    } else {
      return "Erro ao criar arquivo contador de chamados";
    }
  }
  my $msgid;
  if (open(CNT, "+<$cfn")) {
    eval "flock(CNT, 2)";
    seek(CNT, 0, 0);
    my $id = <CNT>;
    chomp $id;
    seek(CNT, 0, 0);
    $msgid = $id + 1;
    print CNT "$msgid\n";
    truncate(CNT, tell(CNT));
    close CNT;
  } else {
    return "Erro ao ler arquivo contador de chamados";
  }
  $name =~ s/\|/!/g;
  $subject =~ s/\|/!/g;
  if (open(DB, ">>$datadir/tickets.cgi")) {
    eval "flock(DB, 2)";
    seek(DB, 0, 2);
    print DB "$msgid|$from|$name|$subject|$tm\n";
    close DB;
    umask(0000);
    chmod 0766, "$datadir/tickets.cgi";
  } else {
    return "Error updating ticket database";
  }
  if (open(MSG, ">$datadir/$msgid.cgi")) {
    print MSG $message;
    close MSG;
    umask(0000);
    chmod(0777, "$datadir/$msgid.cgi");
  } else {
    return "Error writing message file";
  }
  $ticket->{id} = $msgid;
  return undef;
}
# ====================================================================== confirm

sub confirm {
  my $ticket = shift;
  my $email = $ticket->{email};
  my $id = $ticket->{id};
  my $name = $ticket->{name};
  my $subject = $ticket->{subject};
  $subject =~ s/</&lt;/g;
  $name =~ s/</&lt;/g;
  print <<EOT;
<table width=650>
  <tr>
    <td align=left><br>
	Caro $name</br></br>
	Recebemos sua mensagem <i>$subject</i> e foi criado o número de chamado #<b>$id</b>. Por favor anote e informe este número caso deseje saber o andamento do seu chamado. Informações podem sem solicitadas através do e-mail:
	$email
<br><br>
	
    </td>
  </tr>
</table>
EOT
 HDLMail::sendmail(
   {
       mailer => $mailer,
       smtp => $smtphost,
       to => $notifyaddress,
       from => "\"$companyname\" <$helpdeskaddress>",
       subject => "Ticket [$id], ".$ticket->{subject},
       msg => "New service ticket posted by ".$ticket->{name}." (".$ticket->{email}.")\n".
              "THIS IS A NOTIFICATION MESSAGE ONLY, DO NOT REPLY\nuse an url shown below to access the message and claim an ownership via help desk\n\n".
              $ticket->{message}."\n\nHelp Desk URL:\nhttp://$ENV{HTTP_HOST}$ENV{SCRIPT_NAME}?cmd=helpdesk\n"
    }
  );
}
# ====================================================================== cleanit

sub cleanit {
  my ($query, $input) = @_;
  my $val = $query->param($input);
  $val =~ s/^\s+//;
  $val =~ s/\s+$//;
  $query->param(-name => $input, -value => $val);
  return $val;
}
# ================================================================= updateticket

sub updateticket {
  my $ticket = shift;
  my $fn = "$datadir/tickets.cgi";
  if (!open(DB,"+<$fn")) {
    return "Error updating ticket database";
  }
  eval "flock(DB, 2)";
  my @buff = <DB>;
  chomp @buff;
  my $tdb;
  foreach my $line (@buff) {
    my @fields = split(/\|/, $line);
    my $tik;
    foreach my $fld (@tickfields) {
      $tik->{$fld} = shift @fields;
    }
    $tdb->{$tik->{id}} = $tik;
  }
  $tdb->{$ticket->{id}} = $ticket;
  seek(DB, 0, 0);
  foreach my $id (keys %{$tdb}) {
    my $line;
    my $tik = $tdb->{$id};
    foreach my $fld (@tickfields) {
      my $val = $tik->{$fld};
      $val =~ s/\|/!/g;
      $line .= "$val|";
    }
    print DB "$line\n";
  }
  truncate(DB, tell(DB));
  close(DB);
  umask(0);
  chmod(0777, $fn);
  return undef;
}
# ======================================================================= loaddb

sub loaddb {
  my $fn = "$datadir/tickets.cgi";
  return undef if ! -f $fn;
  if (!open(DB, $fn)) {
    return "Error reading ticket database";
  }
  my @buff = <DB>;
  close DB;
  chomp @buff;
  foreach my $line (@buff) {
    my @fields = split(/\|/, $line);
    my $tik;
    foreach my $fld (@tickfields) {
      $tik->{$fld} = shift @fields;
    }
    $ticketdb->{$tik->{id}} = $tik;
  }
  return undef;
}
