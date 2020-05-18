#!/bin/bash
# Brad Riley 1/31/2020
# Removed expired user accounts that have been expired for at least one month.

# Timestamp for the log
DATE=`date "+%Y%m%d"`

IFS=':'
# Iterate through passwd
while read -r user pass uid gid desc home shell; do
  # 1001 is the group I made for SFTP users
  # User IDs below 999 are system level users.
  if [ $gid == '1001' -a $uid -gt 999 ] 
  then
    # Get the line of "chage -l" that states the account expiration
    # "Account expires                                         : Mar 13, 2020"
    expiration=$(chage -l $user | grep "Account expire")
    # Get just the "Mar"
    month=$(echo $expiration | cut -d " " -f 4)
    # Change it to a number date so 03 in this example
    month=$(date -d "${month} 1" +%m)
    # Cut to just "13,"
    day=$(echo $expiration | cut -d " " -f 5)
    # Remove the comma: "13"
    day=$(echo ${day//,})
    # Get the year: 2020
    year=$(echo $expiration | cut -d " " -f 6)
    # Get todays date as: 2020-03-05
    today=$(date +"%Y-%m-%d")
    # Todays date in seconds (since epoch)
    today=$(date -d $today +%s)
    # Add a month to the expiration date
    expire_date=$(date -d "${year}${month}${day}+1 month" +%Y-%m-%d)
    # Convert the expiration date to seconds (since epoch)
    expire_date=$(date -d $expire_date +%s)
    # If today in seconds is greater than the accounts expiration date + 1 month in seconds
    # This means the account has been expired longer than a month.
    if [ $today -ge $expire_date ]
    then
      # Delete'em
      /sbin/deluser --remove-home --quiet $user
      # Log it
      echo "$DATE - Deleted user: $user" >> /path/to/log/rem_expired.log
    fi
  fi
done </etc/passwd
