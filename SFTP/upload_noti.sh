#!/bin/bash
# Brad Riley
# Sends emails when files are created under /home in the incoming folders of sftp users.
# Requires msmtp to send emails.

# Directory to monitor
MONITORDIR="/home"
 TO="email@domain.com"
 FROM="localhost@domain.com"
# Start inotify as monitor, recursive, and with events of create.
# Read the output as the variable NEWFILE. (It outputs the file path/name.)
# Example: NEWFILE=/home/test/sftp/INCOMING/test.txt

inotifywait -m -r -e create --format '%w%f' "${MONITORDIR}" | while read NEWFILE # Start the inotify service on /home
do
        IFS='/' read -ra FOLDER <<< "$NEWFILE" # Split the path into an array {home , test , sftp, INCOMING , test.txt}
        user=$(stat -c '%U' $NEWFILE) # Get the owner of the file that was created
        file="${FOLDER[5]}" # Filename of the file created
        incoming="${FOLDER[4]}" # Verifying the 4th index of the array is the word incoming
        echo $NEWFILE # Print the file created
        # Only send an email if the change  is created in an INCOMING folder and is a file
        if [[ $incoming == "INCOMING" && $user != "root" && $NEWFILE != *".filepart" ]] ; then
          printf "To: $TO\nFrom: $FROM\nSubject: $user has uploaded a file\n\nThe following file has been uploaded: ${NEWFILE}" | msmtp email@domain.com
        fi
done
