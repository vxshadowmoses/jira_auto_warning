#!/usr/bin/python3.7
import optparse
import datetime
import pdb
from requests.auth import HTTPBasicAuth
import requests
import smtplib
import sys
import re

ALL_PROJECTS = "GPE,FSE,FOO"


def get_resource(story, user, api_token):  
    data = get_resource_all(story, user, api_token)
   
   

    #pdb.set_trace()
    tpr = ResourceData()
    

    if "aggregatetimeoriginalestimate" in data['fields']:
        aggr = int(data['fields']['aggregatetimeoriginalestimate']) if data['fields']['aggregatetimeoriginalestimate'] else 0 
        tpr.original_estimation = aggr/60/60
    if "timeSpentSeconds" in data['fields']['timetracking']:
        tpr.hours_spent = int(data['fields']['timetracking']['timeSpentSeconds'])/60/60
    if "updated" in data['fields']:
        tpr.last_update = data['fields']['updated']
    if "name" in data['fields']['status']:
        tpr.status = data['fields']['status']['name']
    if "customfield_10405" in data['fields'] and data['fields']['customfield_10405'] is not None:
        tpr.story_point = int(data['fields']['customfield_10405'])
    if "labels" in data['fields']:
        tpr.labels = data['fields']['labels']  
    if "subtasks" in data['fields']:
        for sub in data['fields']['subtasks']:
            tpr.subtasks+=sub['key']+" "  
    return tpr



class ResourceData:
    def __init__(self):
        self.hours_spent = 0
        self.last_update = ""
        self.status = ""
        self.story_point = 0
        self.labels = []
        self.original_estimation = 0
        self.subtasks= ""
    
    def serialize(self):
        return{
            'hours_spent' : self.hours_spent,
            'last_update' : self.last_update,
            'status' : self.status,
            'estimate' : self.story_point
        }
   
class Issue:
    def __init__(self):
        self.id = ""
        self.summary = ""
        self.resource = ResourceData()
    def serialize(self):
        return {
            'id': self.id, 
            'summary': self.summary,
            'resource': self.resource.serialize()
            
        }

def get_issues(project_id, user, api_token):
    url = 'https://#JIRAURL#/rest/api/3/issue/picker'
        
    auth = HTTPBasicAuth(user, api_token)
    
    headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
    }
    query = {
        'currentProjectId': '{}'.format(project_id),
        'currentJQL' :  'order by status DESC',
        'showSubTasks' : True
        }
    
    response = requests.request(
                        "GET",
                        url,
                        headers=headers,
                        params=query,
                        auth=auth)

    
    return response.json()

def search_issues(project_id, user, api_token):
    url = "https://#JIRAURL#/rest/api/3/search"

    auth = HTTPBasicAuth(user, api_token)
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


    query = {
        'jql': "project = {}".format(project_id),
        'maxResults': "5000"
    }


    response = requests.request(
                        "GET",
                        url,
                        headers=headers,
                        params=query,
                        auth=auth)

    return response.json()


def get_resource_all(story, user, api_token):
    r = requests.get('https://#JIRAURL#/rest/api/latest/issue/{}'.format(story), auth=HTTPBasicAuth(user, api_token))
    return r.json()



parser = optparse.OptionParser()

origin_est_lst = []
worklog_lst = []

parser.add_option('-p', '--project',
    action="store", dest="project",
    help="project id (FOO, FSE, GPE)", default="")

parser.add_option('-l', '--labels',
    action="store", dest="labels",
    help="comma separated list for label filters")

parser.add_option('-o', '--html',
    action="store_true", dest="ouput_html",
    help="output in html format")

parser.add_option('-a', '--audit',
    action="store_true", dest="audit",
    help="perform audit")


parser.add_option('-d', '--data',
    action="store", dest="from_data",
    help="from data")

parser.add_option('-t', '--task',
    action="store", dest="task",
    help="lookup on specific task")

issues_list = []

options, args = parser.parse_args()

USER = "#USER#"
API_TOKEN = "#APITOKEN#"

def pprint(data, htmlOut):
    if not htmlOut:
        pass
        #print(data)
def reporthtml(output, proj):
    
    print("<html>")
    print("<head>")
    print("<title>Report {}</title>".format(proj))
    print("</head>")
    print("<h2>Report {}</h2>".format(proj))
    for line in output:
        if isinstance(line, list):
            for txtline in line:
                print("<p>{}</p>".format(txtline))
        else:
            print("<p>{}</p>".format(line))
    print("</html>")




def show(issue, iss, sum_wl, sum_sp, sum_original, html_print, from_date, audit):
    output = []
    
    if(issue['fields']['issuetype']['subtask']):
        return output
    if from_date:
        created = datetime.datetime.strptime(issue['fields']['created'].split('T')[0], '%Y-%m-%d')
        startdate = datetime.datetime.strptime(from_date, '%Y-%m-%d')
        
        if created < startdate:
            return []
    anomalia = False
    wmissing = False
    simissing = False
    stmissing = False

   
    if audit:
        if int(iss.hours_spent) <= 0 and (iss.status.lower().find('completata')>=0 or iss.status.lower().find('test')>=0):
            wmissing = True
            anomalia = True
        if int(iss.original_estimation) <= 0 and (iss.status.lower().find('completata')>=0 or iss.status.lower().find('test')>=0 or iss.status.lower().find('selected')>=0 or iss.status.lower().find('corso')>=0):
            simissing = True
            anomalia = True
        if len(iss.subtasks)<=0 and (iss.status.lower().find('completata')>=0 or iss.status.lower().find('test')>=0 or iss.status.lower().find('corso')>=0):
            stmissing = True
            anomalia = True
            
    if anomalia:

        pprint("", html_print)
        pprint("", html_print)
        pprint("TASK: {}".format(issue['key']),html_print)
        output.append("TASK: {}".format(issue['key']))
        try:
            pprint("ASSIGNEE: {}".format(issue['fields']['assignee']['displayName']), html_print)
            output.append("ASSIGNEE: {}".format(issue['fields']['assignee']['displayName']))
        except:
            pass
        
        created = issue['fields']['created'].split('T')[0]
        created_frm = created.split('-')
        created = "{}/{}/{}".format(created_frm[2], created_frm[1], created_frm[0])

        pprint("CREATED: {}".format(created), html_print)
        output.append("CREATED: {}".format(created))

        pprint("STATUS: {}".format(iss.status), html_print)
        output.append("STATUS: {}".format(iss.status))

        pprint("SUMMARY: {}".format(issue['fields']['summary'][0:100].encode('utf-8')), html_print)
        output.append("SUMMARY: {}".format(issue['fields']['summary'].encode('utf-8')))

        
        pprint("ANOMALIE:", html_print)
        output.append("ANOMALIE:")

        if wmissing:
            pprint("    [-] worklog mancante", html_print)
            output.append("    [-] worklog mancante")
        if simissing:
            pprint("    [-] stima iniziale mancante", html_print)
            output.append("    [-] stima iniziale mancante")
            
        if stmissing:
            pprint("    [-] subtask tecnici non trovati",  html_print)
            output.append("    [-] subtask tecnici non trovati")
    pprint("",  html_print)
    output.append("")
    return output

def sum_hours(iss, sum_wl, sum_sp, sum_original):
    sum_wl=sum_wl+iss.hours_spent
    sum_sp=sum_sp+iss.story_point
    sum_original=sum_original+iss.original_estimation

    return sum_wl, sum_sp, sum_original


def query_tasks(sum_wl, sum_sp, sum_original, audit, issue, label_filter, output, report_html, from_date):
    iss = get_resource(issue['key'], USER, API_TOKEN)
    if len(label_filter)>0:
        for lbl in label_filter:
            if lbl.strip().lower() in iss.labels:
                sum_wl, sum_sp, sum_original = sum_hours(iss, sum_wl, sum_sp, sum_original)
                origin_est_lst.append(iss.original_estimation)
                worklog_lst.append(iss.hours_spent)
                output = show(issue, iss, sum_wl, sum_sp, sum_original,report_html, from_date, audit)
                break
    else:
        sum_wl, sum_sp, sum_original = sum_hours(iss, sum_wl, sum_sp, sum_original)
        output = show(issue, iss, sum_wl, sum_sp, sum_original,report_html,from_date,audit)
    return sum_wl, sum_original, sum_sp, output

def do_audit(search_issues, options, USER, API_TOKEN, reporthtml, query_tasks, proj_id):
    data = search_issues(proj_id, USER, API_TOKEN)

    if options.labels:
        label_filter = options.labels.split(',')
    else:
        label_filter = []

    if options.ouput_html:
        report_html = True
    else:
        report_html = False

    if options.from_data:
        from_date = options.from_data
    else:
        from_date = ""

    if options.task:
        task = options.task
    else:
        task = ""

    if options.audit:
        audit = True
    else:
        audit = False



    sum_wl = 0
    sum_sp = 0
    sum_original = 0
    output = []
   


    for issue in data['issues']:
    
        if len(task)>0:
            if task==issue['key']:
                sum_wl, sum_original, sum_sp, out_task = query_tasks(sum_wl, sum_sp, sum_original, audit, issue, label_filter, output, report_html, from_date)
        else:
            sum_wl, sum_original, sum_sp, out_task = query_tasks(sum_wl, sum_sp, sum_original, audit, issue, label_filter, output, report_html, from_date)
        output.append("\n".join(out_task))

    if report_html:
        reporthtml(output, proj_id)

    return output


if len(options.project)>0:
    proj_id = options.project.strip()
else:
    proj_id = ALL_PROJECTS

output = []
if proj_id.find(",")>=0:
    projects = proj_id.split(',')
    for proj in projects: 
        out_task = do_audit(search_issues, options, USER, API_TOKEN, reporthtml, query_tasks, proj)
        output.append("\n".join(out_task))
else:
    output = do_audit(search_issues, options, USER, API_TOKEN, reporthtml, query_tasks, proj_id)


mail_ouput = ""
if len(output)>0:
    
    mail_ouput = mail_ouput+"\n"
    mail_ouput = mail_ouput+"\n".join(output)
    mail_ouput = re.sub(r'\n{2,}','\n',mail_ouput)
    mail_ouput = mail_ouput.replace("TASK:","\n\n_________\n\nTASK:")
    


gmail_user = '#MAIL#'
gmail_password = '#MAILPSW#'
to_mails = "#MAIL1#, #MAIL12#, #MAIL3#"
sent_from = gmail_user
to =[]
for email in to_mails.split(","):
    to.append(email.strip())


body=""
subject = "Report anomalie JIRA Feltrinelli"
body = mail_ouput
    


email_text = """\
From: %s
To: %s
Subject: %s

%s
""" % (sent_from, ", ".join(to), subject, body)


server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.ehlo()
server.login(gmail_user, gmail_password)
server.sendmail(sent_from, to, email_text.strip())
server.close()

print('Email sent!')
    


    

