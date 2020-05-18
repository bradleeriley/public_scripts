#!/bin/bash
# Brad Riley
# ECG
# Sends emails when files are created under /home in the incoming folders of sftp users.
# Requires msmtp

# Directory to monitor
MONITORDIR="/home"

# Start inotify as monitor, recursive, and with events of create.
# Read the output as the variable NEWFILE. (It outputs the file path/name.)
# Example: NEWFILE=/home/test/sftp/INCOMING/test.txt

inotifywait -m -r -e create --format '%w%f' "${MONITORDIR}" | while read NEWFILE
do
        IFS='/' read -ra FOLDER <<< "$NEWFILE" # Split the path into an array {home , test , sftp, INCOMING , test.txt}
        user=$(stat -c '%U' $NEWFILE) # Get the owner of the file that was created
        file="${FOLDER[5]}" # Filename of the file created
        incoming="${FOLDER[4]}" # Verifying the 4th index of the array is the word incoming
        echo $NEWFILE # Print the file created
        # Only send an email if the change  is created in an INCOMING folder and is a file
        if [[ $incoming == "INCOMING" && $user != "root" ]] ; then
          printf "To: recipient@ec-group.com\nFrom: sender@ec-group.com\nSubject: $user has uploaded a file\n\nThe following file has been uploaded: ${NEWFILE}" | msmtp sc@ec-group.com
        fi
done
