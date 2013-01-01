#!/bin/bash

BINDDN="finder"
BINDPW="secure_password"
BASEDN="dc=iib,dc=ua"
LDAP_SERVER="dc2.iib.ua"

CONFIG_PATH="$HOME/.gconf/apps/evolution/mail"
CONFIG_FILE="%gconf.xml"
USER=`whoami`

[ -f $CONFIG_PATH/$CONFIG_FILE ] && exit;

result=`ldapsearch -x -D $BINDDN -w $BINDPW -h $LDAP_SERVER -b $BASEDN -LLL "(sAMAccountName=$USER)" cn mail 2>/dev/null`
cn=`echo "$result" | grep "cn: " | sed 's/cn: //'`
mail=`echo "$result" | grep "mail: " | sed 's/mail: //'`

EMAIL_ADDRESS=$mail
USER_FULL_NAME=$cn
ORGANIZATION="ii-bank.com.ua"
MAPI_URL="mapi://${USER}@ex01/;domain=iib.ua;profile=${USER}@iib.ua@ex01;realm"

#<?xml version="1.0"?>
#<gconf>
#	<entry name="signatures" mtime="1328879891" type="list" ltype="string">
#	</entry>
#	<entry name="default_account" mtime="1328879071" type="string">
#		<stringvalue>1328878928.4541.0@test-hq-pc</stringvalue>
#	</entry>
#	<entry name="accounts" mtime="1328879976" type="list" ltype="string">
#		<li type="string">
#            <stringvalue>
DATA="<?xml version='1.0'?><account name='${EMAIL_ADDRESS}' uid='1328878928.4541.0@test-hq-pc' enabled='true'><identity><name>${USER_FULL_NAME}</name><addr-spec>${EMAIL_ADDRESS}</addr-spec><organization>${ORGANIZATION}</organization><signature uid=''/></identity><source save-passwd='true' keep-on-server='false' auto-check='true' auto-check-timeout='1'><url>${MAPI_URL}</url></source><transport save-passwd='true'><url>${MAPI_URL}</url></transport><drafts-folder>folder://local/Drafts</drafts-folder><sent-folder>folder://local/Sent</sent-folder><auto-cc always='false'><recipients></recipients></auto-cc><auto-bcc always='false'><recipients></recipients></auto-bcc><receipt-policy policy='ask'/><pgp encrypt-to-self='true' always-trust='false' always-sign='false' no-imip-sign='false'/><smime sign-default='false' encrypt-default='false' encrypt-to-self='true'/></account>"

#</stringvalue>
#		</li>
#	</entry>
#	<entry name="send_recv_all_on_start" mtime="1328879870" type="bool" value="false"/>
#	<entry name="send_recv_on_start" mtime="1328879870" type="bool" value="true"/>
#</gconf>"

gconftool-2 --type list --list-type string --set /apps/evolution/mail/accounts "[${DATA}]"
gconftool-2 --type string --set /apps/evolution/mail/default_account "1328878928.4541.0@test-hq-pc"

