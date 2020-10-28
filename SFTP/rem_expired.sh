#!/bin/bash

# Brad Riley
# ECG
# Removes expired accounts and their home directories the 1st of every month.

DATE=`date "+%Y%m%d"`
LOGDIR='/home/someuser/filename.log'
IFS=':'

while read -r user pass uid gid desc home shell; do
  if [ $gid == '1001' -a $uid -gt 999 ]
  then
    expiration=$(chage -l $user | grep "Account expire")
    month=$(echo $expiration | cut -d " " -f 4)
    month=$(date -d "${month} 1" +%m)
    day=$(echo $expiration | cut -d " " -f 5)
    day=$(echo ${day//,})
    year=$(echo $expiration | cut -d " " -f 6)
    today=$(date +"%Y-%m-%d")
    today=$(date -d $today +%s)
    expire_date=$(date -d "${year}${month}${day}+1 month" +%Y-%m-%d)
    echo 'date -d "${year}${month}${day}+1 month" +%Y-%m-%d'
    echo "$expire_date"
    expire_date=$(date -d $expire_date +%s)
    echo 'date -d $expire_date +%s'
    echo "$expire_date"
    if [ $today -ge $expire_date ]
    then
      /sbin/deluser --remove-home --quiet $user
      echo "$DATE - Deleted user: $user" >> $LOGDIR
    fi
  fi
done </etc/passwd
