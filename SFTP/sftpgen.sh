#!/bin/bash
#include <stdio.h>
# SFTP Account generator
# Brad Riley 11/20/2019

# Generates SFTP users with a username of an integer larger than 1001 that expire after 2 weeks.
# Generates UP/DOWN directories and assigns permissions for.
# If user already exists, asks to extend expiration and/or reset password.

# Script must be ran as root
if [[ $EUID -ne 0 ]]; then
   printf "\nThis script must be run as root\n"
   printf "su -c ./sftpgen.sh\n\n"
   exit 1
fi

trap "echo ; exit 130" INT

# Welcome screen
printf "\n#######################################\n"
printf "\e[31;1mWelcome to sftpgen!\n\e[0m"
printf "If you would like to generate \e[31;1mnew\e[0m SFTP credentials, type in an\e[31;1m unused\e[0m ticket number.\nIf you would like to\e[31;1m reset\e[0m the password or\e[31;1m extend\e[0m the expiration date of a sftp user, first type in its\e[31;1m existing\e[0m ticket number listed below.\nUse \e[31;1mCTRL+C\e[0m to exit sftpgen at anytime."

# Print existing sftp users by iterating through passwd
# Print expiration date
IFS=':'
printf "\n\nExisting ticket numbers: \n"
printf "Ticket - Expiration date\n"
while read -r user pass uid gid desc home shell; do
  if [[ $gid == '1001' ]]
  then
    expiration=$(chage -l $user | grep "Account expire") 
    month=$(echo $expiration | cut -d " " -f 4) 
    month=$(date -d "${month} 1" +%m) day=$(echo $expiration | cut -d " " -f 5) 
    day=$(echo ${day//,})
    year=$(echo $expiration | cut -d " " -f 6)
    printf "%6d - %s\n" $user "$month/$day/$year"
  fi
done </etc/passwd

# Get the ticket number / username. Only allow integers larger than 1001.
printf "Only numbers above 1001 are valid input, no symbols.\n\n"
read -p 'Enter Ticket number # ' ticketvar
while [[ !( $ticketvar =~ ^[0-9]+$ ) || $ticketvar -lt 1001 ]] ; do
  printf "\nERROR: Only numbers above 1001 are valid input.\n"
  read -p 'Enter Ticket number # ' ticketvar
  done

# Check if the user exists.
check_user=$(grep -c "$ticketvar" /etc/passwd)

# 14 day expiration date across the board.
expire=$(date -d '+14 days' '+%Y-%m-%d')

# Generate a password
userpass=$(date | sha256sum | base64 | head -c 8)

# Check if user exists
if [ "$check_user" == "1" ] ; then
  endstring=""
  printf "*** \e[31;1mUser already exists!\e[0m ***\n"
  read -p "Extend expiration to "$expire"? [y/n] # " renew # Extend expiration date two weeks from today
  if [ $renew == 'y' ]
    then
      chage -E $expire $ticketvar
    fi
    read -p 'Would you like to reset the password? [y/n] # ' reset # Reset password
    if [ $reset == 'y' ] ; then
      echo "$ticketvar:$userpass" | /sbin/chpasswd
      creds="\n  Username: $ticketvar \n  Password: $userpass \n"
      printf "$creds"
      if [ $renew == 'y' ]
        then
          printf "  Expiration: $expire \n"
      fi
      printf "\n\e[31;1mWARNING:\e[0m Record credentials! as they can only be reset once created.\n\n"
    fi
else # Create user
  /usr/sbin/useradd --expiredate $expire -g sftpusers -s /bin/false -m -d /home/$ticketvar $ticketvar
  echo "$ticketvar:$userpass" | /sbin/chpasswd
  chown root:transfer /home/$ticketvar
  mkdir /home/$ticketvar/sftp
  chown root:transfer /home/$ticketvar/sftp
  chmod 755 /home/$ticketvar/sftp
  chmod 755 /home/$ticketvar
  mkdir /home/$ticketvar/sftp/{INCOMING,OUTGOING}
  chmod 775 /home/$ticketvar/sftp/INCOMING
  chmod 575 /home/$ticketvar/sftp/OUTGOING
  chown $ticketvar:transfer /home/$ticketvar/sftp/{INCOMING,OUTGOING}
  chmod g+s /home/$ticketvar/sftp/INCOMING
  creds="\n  Username: $ticketvar \n  Password: $userpass \n  Expiration: $expire\n\n"
  printf "$creds"
  printf "\e[31;1mWARNING:\e[0m Record credentials! as they can only be reset once created.\n\n"
fi
