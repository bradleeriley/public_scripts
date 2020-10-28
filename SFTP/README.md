# SFTP

These are scripts I made to run on a Debian server serving as our SFTP server. I learned how to properly secure an exposed device, from SELinux to SFTP specific permissions. 

`sftpgen.sh` - This script ran the user through a wizard to create a user, set an expiration date 2 weeks in advance, created the UP and DOWN directories with proper permissions, and provided the credentials for the user.

`upload_noti.sh` - Sends email notifications when writing operations end to an email of your choice using MSMTP. Includes the name of the file that was uploaded and user that uploaded the file in email.

`rem_expired.sh` - Deleted expired accounts and its home directory. Logs actions to file. Only run when you are ready to delete the expired accounts. Recommend running once every month.