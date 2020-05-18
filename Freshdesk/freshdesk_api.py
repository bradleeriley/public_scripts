# When Check Point SR update ticket comes in copy them to the corresponding ticket in freshdesk.
# Grabs list of unresolved tickets, posts note to FD ticket, puts FD in open, deletes CP update FD ticket.
# Brad Riley
# 4.26.2019

import requests
import json
import re
import dateutil.parser
import math
from datetime import datetime
from dateutil import tz


# Remove images from HTML body of Check Point update email
def cleanhtml(data):
    clean_data = re.sub("(<img.*?>)", "", data, 0, re.IGNORECASE | re.DOTALL | re.MULTILINE)
    return clean_data

# Removes new lines that occur more than once in a row
def clean_description(description):
    new_descrip = description.split('<br>')
    index = 0
    found_newline = 0
    newline_index = []
    while index < (len(new_descrip) - 1):
        if new_descrip[index] == '\n':
            found_newline += 1
        else:
            found_newline = 0
        if found_newline >= 2:
            newline_index.append(index)
        index += 1
    removed = 0
    for i in newline_index:
        del new_descrip[i - removed]
        removed += 1
    new_descrip = '<br>'.join(new_descrip)
    return new_descrip

def clean_salesforce(description):
    description = description.split('</span>')
    description = description[0]
    description = description.split('!important">')
    description = description[1]
    return description

# Converts the date submitted value in the ticket to CST / Local
def utc_to_local(utc_dt):
    utc_dt = dateutil.parser.parse(utc_dt)
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()
    utc_dt = utc_dt.replace(tzinfo=from_zone)
    return utc_dt.astimezone(to_zone)

# Sorts the list by the ticket ID [lowest, ... , highest] to submit updates in chronological order
def sort_tickets(tickets):
    ticket_ids = []
    for each_ticket in tickets:
        if each_ticket['id'] not in ticket_ids:
            ticket_ids.append(each_ticket['id'])
    ticket_ids = sorted(ticket_ids)    
    sorted_tickets =[]
    for each_id in ticket_ids:
        for each_ticket in tickets:
            if each_ticket['id'] == each_id:
                sorted_tickets.append(each_ticket)
    return sorted_tickets

domain = '' # Domain i.e company.freshdesk.com
api_key = '' # API key
headers = { 'Content-Type' : 'application/json' } # Required for creating the note
log = open("freshdesk_api.log","a+")

# Grabs the first page of unresolved tickets - "open", "pending", and "waiting on third party" then interprets the json
unresolved_tickets = (requests.get("https://"+ domain +'/api/v2/search/tickets?query="status:2%20OR%20status:3%20OR%20status:7"&page=1', auth=(api_key, ''))).json() 

# Freshdesk only gives us 30 results at a time. 
# At the end of the request is the total number of results (located in unresolved_tickets['total']).
# totalPages = the total number of pages
# Divide as much as you can, but round up. So 81/30 = 4 (actually 3.03). This is to get the last few results on the last page.
totalPages = math.ceil(unresolved_tickets['total'] / 30)
for i in range(2,totalPages+1):
    unresolved_tickets_nextPage = (requests.get("https://"+ domain +'/api/v2/search/tickets?query="status:2%20OR%20status:3%20OR%20status:7"&' + 'page=' + str(i), auth=(api_key, ''))).json()
    unresolved_tickets['results'] = unresolved_tickets['results'] + unresolved_tickets_nextPage['results']
    #print("https://"+ domain +'/api/v2/search/tickets?query="status:2%20OR%20status:3%20OR%20status:7"&' + 'page=' + str(i))

# Where Check Point update tickets are stored if found
update_tickets = []
junk_tickets = []
updateTicket_descriptions = []
# If the subject of the ticket contains the str "sr", is "open", and was opened by Check Point.
for i in unresolved_tickets['results']:
    ticket = dict(i)
    #print(ticket['subject'])
    checkpoint_id = '1003252354'
    checkpoint_update = ('sr' in ticket['subject'].lower() and ticket['status'] == 2 and '[ ref:' in ticket['subject'].lower())
    chatter_update = ('sr' in ticket['subject'].lower() and ticket['status'] == 2 and 'posted' in ticket['subject'].lower())
    salesforce_update = ('commented on your post on Case: ' in ticket['subject'] and ticket['status'] == 2)
    status_change = ('Status has been changed' in ticket['subject'])
    solution_provided = ('Status has been changed to Solution Provided' in ticket['subject'])
    new_sr = ("New Support Service Request" in ticket['subject'] and "has been created" in ticket['subject'])
    if salesforce_update:
        #print('Found a sales force update!')
        ticket['description'] = clean_salesforce(ticket['description'])
    if status_change or solution_provided or new_sr:
        junk_tickets.append(ticket)
        #print('Found junk ticket - ' + str(ticket['id']))
    elif checkpoint_update or chatter_update or salesforce_update:
        if ticket not in update_tickets and (ticket['description'] not in updateTicket_descriptions):
            #print('Found update ticket - ' + str(ticket['id']))
            update_tickets.append(ticket)
            timestamp = str(datetime.now())
            log.write(timestamp + str(ticket['id']) + ' - Found update ticket\n')
            updateTicket_descriptions.append(ticket['description'])
        elif ticket['description'] in updateTicket_descriptions:
            junk_tickets.append(ticket)
            #print('Found duplicate ticket - ' + str(ticket['id']))

# If an update_ticket was found, try to find the FD ticket. If not, then exit.
#print(update_tickets)

if update_tickets or junk_tickets:
    timestamp = str(datetime.now())
    log.write(timestamp + ' - ' + "Started\n")

# Set to true in case there are no update tickets

posted = True
update_ticket_ids = []

if update_tickets:
    posted = False
    update_tickets = sort_tickets(update_tickets)
    for ticket in update_tickets:
        salesforce_update = ('commented on your post on Case: ' in ticket['subject'] and ticket['status'] == 2)
        date_submitted = utc_to_local(ticket['created_at'])
        update_ticket_id = ticket['id']
        update_ticket_subject = ticket['subject']
        if salesforce_update:
            sr = (re.search(r'(\d-\d{10})', update_ticket_subject)).group(1)
            ticket_descrip = ticket['description']
            ticket_descrip = ticket_descrip.replace('\n','<br>\n<br>')
            ticket_descrip = clean_description(ticket_descrip)
            description = str(date_submitted) + ' | Check Point update ticket #' + str(update_ticket_id) + ' - ' + sr + '<br>\n<br>' + ticket_descrip
            #print(sr)
            #print(repr(description))
        else:
            sr = (re.search(r'SR( )?#(\d-\d{10})', update_ticket_subject)).group(2) # From the Check Point update ticket, get the SR.
            description = str(date_submitted) + '<br>\n<br>' + cleanhtml((update_ticket_subject + '\n') + ticket['description'])
            description = clean_description(description)
        body = {'body' : description}
        for each_ticket in unresolved_tickets['results']:
            # Finds any unresolved ticket with the SR in the subject that is not itself.
            #print(each_ticket['subject'])
            if sr in each_ticket['subject'] and each_ticket['subject'] != update_ticket_subject and each_ticket['requester_id'] != 1003252354:
                # Copies the body of the update ticket and creates a note on the corresponding FD ticket.
                #print('Created a note on ticket - ' + str(each_ticket['id']))
                post = requests.post("https://"+ domain +"/api/v2/tickets/" + str(each_ticket['id']) + "/notes", auth = (api_key, ''), headers = headers, data = json.dumps(body))
                timestamp = str(datetime.now())
                log.write(timestamp + ' - ' + str(each_ticket['id']) + " - Note created\n")
                
                # Set ticket to "open"
                if each_ticket['status'] != 2:
                    #print('Setting ticket to open - ' + str(each_ticket['id']))
                    put = requests.put("https://"+ domain +"/api/v2/tickets/" + str(each_ticket['id']), auth = (api_key, ''), headers = headers, data = json.dumps({"status" : 2}))
                    timestamp = str(datetime.now())
                    log.write(timestamp + ' - ' + str(each_ticket['id']) + " - Set to open\n")
                
                # Delete the Check Point update ticket
                #print('Deleting ticket - ' + str(each_ticket['id']))
                delete = requests.delete("https://"+ domain +"/api/v2/tickets/" + str(update_ticket_id), auth = (api_key, ''), headers = headers)
                timestamp = str(datetime.now())
                log.write(timestamp + ' - ' + str(update_ticket_id) + " - Deleted\n")
                # Found the parent so set it to posted.
                posted = True
        if posted == False:
            update_ticket_ids.append(ticket['id'])
    if junk_tickets == False:
        timestamp = str(datetime.now())
        log.write(timestamp + ' - ' + "Finished\n")
if junk_tickets:
    for ticket in junk_tickets:
        update_ticket_id = ticket['id']
        update_ticket_subject = ticket['subject']
        #print('Deleting Junk - ' + str(update_ticket_id))
        delete = requests.delete("https://"+ domain +"/api/v2/tickets/" + str(update_ticket_id), auth = (api_key, ''), headers = headers)
        timestamp = str(datetime.now())
        log.write(timestamp + ' - ' + str(update_ticket_id) + " - Deleted Junk\n")
    timestamp = str(datetime.now())
    log.write(timestamp + ' - ' + "Finished\n")
#print('Finished!')

if update_ticket_ids:
    timestamp = str(datetime.now())
    log.write(timestamp + ' - ' + "Error! Found update tickets but did not find parent: ", update_ticket_ids, "\n")

log.close()
