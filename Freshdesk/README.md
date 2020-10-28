# Freshdesk

`cpreply_fdapi.py` - I ran into a problem that a specific vendor's replies would come into Freshdesk as a new ticket. This script was ran on a cron job every 2 minutes to check for the vendor's replies, then append those replies as a private note to the parent Freshdesk ticket, and set the ticket as open. This was my first time touching a web API.