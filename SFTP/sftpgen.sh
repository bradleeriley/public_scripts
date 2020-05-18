#!/bin/bash
# SFTP Account generator
# Brad Riley 11/20/2019

# Generates SFTP users with a username of an integer larger than 1001 that expire after 2 weeks.
# Generates UP/DOWN directories and assigns permissions for the created user.
# If user already exists, asks to extend expiration and/or reset password.

if [[ $EUID -ne 0 ]]; then
   printf "\nThis script must be run as root\n"
   printf "su -c ./sftpgen.sh\n\n"
   exit 1
fi

IFS=':'
printf "\nExisting SFTP users: \n"
while read -r user pass uid gid desc home shell; do
  if [[ $gid == '1001' ]]
  then
    printf $user"\n"
  fi
done </etc/passwd

# Get the ticket number / username. Only allow integers larger than 1001.
printf "Do not include the # symbol\n"
ticketvar=""
while [[ !( $ticketvar =~ ^[0-9]+$ ) || $ticketvar -lt 1001 ]] ; do
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
  printf "*** User already exists! ***\n"
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
          printf "  Expiration: $expire \n\n"
      fi
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
  chmod 755 /home/$ticketvar/sftp/INCOMING
  chmod 575 /home/$ticketvar/sftp/OUTGOING
  chown $ticketvar:transfer /home/$ticketvar/sftp/{INCOMING,OUTGOING}
  creds="\n  Username: $ticketvar \n  Password: $userpass \n  Expiration: $expire\n\n"
  printf "$creds"
fi
