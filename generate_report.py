import config
import csv
import getopt
import json
import phabricator.conduit
import sys
import time
from datetime import datetime


def print_help():
    print('generate_report.py -p <project name> -t <task id>')
    print('or generate_report.py --project <project name> --task <task id>')
    print('Either project name is required')
    print('Eg. generate_report.py -p "This is project name"')
    print('Eg. generate_report.py -t "T1234')
    print('Eg. generate_report.py -p "This is project name" -t "T1234')
    print('Eg. generate_report.py --project "This is project name" --task "T1234')
    print("generate_report.py -h for usage help")


def format_datetime(epoch):
    return time.strftime(config.DATE_TIME_FORMAT, time.localtime(int(epoch)))


def get_csv_length(filename):
    length = 0
    try:
        with open(filename, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for _ in reader:
                length += 1
            return length
    except FileNotFoundError:
        f = open(filename, 'x')
        f.close()
        return length


def write_in_csv(filename, data, source='dict', write_mode='a'):
    if data is None:
        return
    length = get_csv_length(filename)
    with open(filename, write_mode) as csvfile:
        if source == 'list':
            writer = csv.writer(csvfile)
        else:
            writer = csv.DictWriter(csvfile, fieldnames=data.keys())
        if length == 0 and source == 'dict':
            writer.writeheader()
        writer.writerow(data)


def format_start_end_dates(start_date_list,end_date_list):
    export_user_dates = []
    export_user_date = ""
    export_user_start_dates = start_date_list
    export_user_end_dates = end_date_list
    for i in range(len(export_user_start_dates)):
        if i < len(export_user_start_dates):
            export_user_date = export_user_start_dates[i]
        if i < len(export_user_end_dates):
            export_user_date += " - " + export_user_end_dates[i]
        export_user_dates.append(export_user_date)
    return export_user_dates


def construct_csv():
    today = datetime.now()
    report_date = today.strftime(config.DATE_TIME_FORMAT_FILENAME)
    statuses_to_ignore = list(config.STATUSES_TO_IGNORE)
    subtype_to_ignore = list(config.SUBTYPE_TO_IGNORE)
    report_file_name = ""

    with open('reports/export.json', 'r') as f:
        projects = json.load(f)
    if projects is not None and issubclass(type(projects), dict) and len(projects) > 0:
        for project in dict(projects).values():
            if "tasks" in project and project['tasks'] is not None:
                for project_task in dict(project['tasks']).values():
                    task_details_to_be_exported = {}
                    waiting_for_user = {'start': [], 'end': []}
                    ps_in_progress = {'start': [], 'end': []}
                    dev_in_progress = {'start': [], 'end': []}
                    review_in_progress = {'start': [], 'end': []}
                    qa_in_progress = {'start': [], 'end': []}
                    promoted_to_staging = {'start': [], 'end': []}
                    task_revision_details = []
                    task_revision_author_details = []
                    task_revision_reviewer_comment_details = []
                    task_revision_total_comment_details = []

                    qa_cycles = 0
                    review_cycles = 0
                    ps_cycles = 0
                    product_requirement_cycles = 0
                    release_date = ""
                    if "details" in project_task and project_task['details'] is not None:
                        project_task_details = project_task['details']
                        if project_task_details is not None and type(project_task_details) == dict:
                            if "status" in project_task_details and project_task_details["status"] is not None and project_task_details["status"] in statuses_to_ignore:
                                continue
                            if "subtype" in project_task_details and project_task_details["subtype"] is not None and project_task_details["subtype"] in subtype_to_ignore:
                                continue

                            task_details_to_be_exported['Phab ID'] = project_task_details['objectName']
                            task_details_to_be_exported['Title'] = project_task_details['title']
                            # task_details_to_be_exported['Task URL'] = project_task_details['uri']
                            task_details_to_be_exported['Comment'] = " "
                            task_details_to_be_exported['Delivery Date'] = " "

                            if "subtype" in project_task_details:
                                task_details_to_be_exported['Task Type'] = str(project_task_details['subtype']).title()
                            else:
                                task_details_to_be_exported['Task Type'] = 'Task'
                            task_details_to_be_exported['Current Status'] = project_task_details['statusName']

                            user_details = phabricator.conduit.User.get_user_details(phabricator.conduit.User(), project_task_details['ownerPHID'])
                            if user_details is not None and user_details != "" and type(user_details) == dict:
                                task_details_to_be_exported['Assigned To'] = user_details['realName']
                            else:
                                task_details_to_be_exported['Assigned To'] = project_task_details['ownerPHID']

                            waiting_for_user['start'].append(format_datetime(project_task_details['dateCreated']))

                            if "transactions" in project_task and project_task['transactions'] is not None:
                                if "statuses" in project_task['transactions'] and project_task['transactions']['statuses'] is not None:
                                    task_statuses = list(project_task['transactions']['statuses'])
                                    for i in range(len(task_statuses) - 1, -1, -1):
                                        task_status_details = task_statuses[i]
                                        if "oldValue" in task_status_details and task_status_details['oldValue'] is not None:
                                            if task_status_details['oldValue'] in ['open', 'waitingForUser']:
                                                waiting_for_user['end'].append(format_datetime(task_status_details['dateCreated']))
                                            elif task_status_details['oldValue'] in ['psInProgress']:
                                                ps_in_progress['end'].append(format_datetime(task_status_details['dateCreated']))
                                            elif task_status_details['oldValue'] in ['devInProgress']:
                                                dev_in_progress['end'].append(format_datetime(task_status_details['dateCreated']))
                                            elif task_status_details['oldValue'] in ['reviewInProgress']:
                                                review_in_progress['end'].append(format_datetime(task_status_details['dateCreated']))
                                            elif task_status_details['oldValue'] in ['qaInProgress']:
                                                qa_in_progress['end'].append(format_datetime(task_status_details['dateCreated']))
                                            elif task_status_details['oldValue'] in ['promotedToStaging', 'qaVerified']:
                                                promoted_to_staging['end'].append(format_datetime(task_status_details['dateCreated']))

                                        if "newValue" in task_status_details and task_status_details['newValue'] is not None:
                                            if task_status_details['newValue'] in ['open', 'waitingForUser']:
                                                waiting_for_user['start'].append(format_datetime(task_status_details['dateCreated']))
                                            elif task_status_details['newValue'] in ['psInProgress']:
                                                ps_in_progress['start'].append(format_datetime(task_status_details['dateCreated']))
                                            elif task_status_details['newValue'] in ['devInProgress']:
                                                dev_in_progress['start'].append(format_datetime(task_status_details['dateCreated']))
                                            elif task_status_details['newValue'] in ['reviewInProgress']:
                                                review_in_progress['start'].append(format_datetime(task_status_details['dateCreated']))
                                            elif task_status_details['newValue'] in ['qaInProgress']:
                                                qa_in_progress['start'].append(format_datetime(task_status_details['dateCreated']))
                                            elif task_status_details['newValue'] in ['promotedToStaging', 'qaVerified']:
                                                promoted_to_staging['start'].append(format_datetime(task_status_details['dateCreated']))

                                        if "oldValue" in task_status_details and task_status_details['oldValue'] is not None \
                                                and "newValue" in task_status_details and task_status_details['newValue'] is not None:
                                            if task_status_details['oldValue'] in ['psInProgress', 'devInProgress', 'reviewInProgress', 'qaInProgress', 'promotedToStaging', 'qaVerified'] \
                                                    and task_status_details['newValue'] in ['open', 'waitingForUser']:
                                                product_requirement_cycles += 1
                                            if task_status_details['oldValue'] in ['reviewInProgress'] \
                                                    and task_status_details['newValue'] in ['devInProgress']:
                                                review_cycles += 1
                                            if task_status_details['oldValue'] in ['waitingForQA', 'qaInProgress', 'qaVerified', 'promotedToStaging'] \
                                                    and task_status_details['newValue'] in ['devInProgress']:
                                                qa_cycles += 1
                                            if task_status_details['oldValue'] in ['devInProgress', 'reviewInProgress', 'waitingForQA', 'qaInProgress', 'qaVerified', 'promotedToStaging'] \
                                                    and task_status_details['newValue'] in ['psInProgress']:
                                                ps_cycles += 1

                                            if task_status_details['newValue'] in ['closed']:
                                                release_date = format_datetime(task_status_details['dateCreated'])

                                if "comments" in project_task['transactions'] and project_task['transactions']['comments'] is not None \
                                        and "revisions" in project_task['transactions'] and project_task['transactions']['revisions'] is not None:
                                    task_revisions_dict = dict(project_task['transactions']['revisions'])
                                    task_revision_comments_dict = dict(project_task['transactions']['comments'])
                                    task_revisions_list = list(task_revisions_dict.values())

                                    for i in range(len(task_revisions_list)):
                                        revision_id = "D" + str(task_revisions_list[i]['id'])
                                        task_revision_detail = task_revisions_dict.get(revision_id)
                                        revision_title = task_revision_detail['fields']['title']
                                        revision_author_details = phabricator.conduit.User.get_user_details(phabricator.conduit.User(), task_revision_detail['fields']['authorPHID'])
                                        if revision_author_details is not None and revision_author_details != "" and type(revision_author_details) == dict:
                                            revision_author_name = revision_author_details['realName']
                                        else:
                                            revision_author_name = task_revision_detail['fields']['authorPHID']
                                        revision_details_to_be_exported = revision_id + " : " + revision_title
                                        revision_author_details_to_be_exported = revision_id + " : " + revision_author_name
                                        task_revision_details.append(revision_details_to_be_exported)
                                        task_revision_author_details.append(revision_author_details_to_be_exported)
                                        task_revision_comment_detail = task_revision_comments_dict.get(revision_id)
                                        total_comment_details = revision_id + " : Total(" + str(task_revision_comment_detail['count']) + "), Done(" + str(task_revision_comment_detail['done']) + ")"
                                        task_revision_total_comment_details.append(total_comment_details)
                                        task_revision_reviewer_details = dict(task_revision_comment_detail['author_wise_count'])
                                        task_revision_reviewer_comment_detail = revision_id + " : "
                                        reviewer_comments = []
                                        for reviewer_phid, reviewer_comments_count in task_revision_reviewer_details.items():
                                            revision_reviewer_details = phabricator.conduit.User.get_user_details(phabricator.conduit.User(), reviewer_phid)
                                            if revision_reviewer_details is not None and revision_reviewer_details != "" and type(revision_reviewer_details) == dict:
                                                revision_reviewer_name = revision_reviewer_details['realName']
                                            else:
                                                revision_reviewer_name = reviewer_phid
                                            reviewer_comment = revision_reviewer_name + "(" + str(reviewer_comments_count) + ")"
                                            reviewer_comments.append(reviewer_comment)
                                        task_revision_reviewer_comment_detail += ", ".join(reviewer_comments)
                                        task_revision_reviewer_comment_details.append(task_revision_reviewer_comment_detail)

                            task_details_to_be_exported['Waiting For User Dates'] = ";    ".join(format_start_end_dates(waiting_for_user['start'], waiting_for_user['end']))
                            task_details_to_be_exported['PS Dates'] = ";    ".join(format_start_end_dates(ps_in_progress['start'], ps_in_progress['end']))
                            task_details_to_be_exported['Dev Dates'] = ";    ".join(format_start_end_dates(dev_in_progress['start'], dev_in_progress['end']))
                            task_details_to_be_exported['CR Dates'] = ";    ".join(format_start_end_dates(review_in_progress['start'], review_in_progress['end']))
                            task_details_to_be_exported['QA Dates'] = ";    ".join(format_start_end_dates(qa_in_progress['start'], qa_in_progress['end']))
                            task_details_to_be_exported['Promoted to Staging Dates'] = ";    ".join(format_start_end_dates(promoted_to_staging['start'], promoted_to_staging['end']))
                            task_details_to_be_exported['Release Date'] = release_date
                            task_details_to_be_exported['Product Requirement Cycles'] = str(product_requirement_cycles)
                            task_details_to_be_exported['PS Cycles'] = str(ps_cycles)
                            task_details_to_be_exported['Review Cycles'] = str(review_cycles)
                            task_details_to_be_exported['QA Cycles'] = str(qa_cycles)
                            task_details_to_be_exported['Task Revisions'] = ";    ".join(task_revision_details)
                            task_details_to_be_exported['Task Revision Authors'] = ";    ".join(task_revision_author_details)
                            task_details_to_be_exported['Code Review Comments By Reviewers'] = ";    ".join(task_revision_reviewer_comment_details)
                            task_details_to_be_exported['Revisions Comments'] = ";    ".join(task_revision_total_comment_details)

                    report_file_name = 'reports/' + project['details']['fields']['name'] + " - " + report_date + ".csv"
                    write_in_csv(report_file_name, task_details_to_be_exported)
    print("Report exported successfully. Check:", report_file_name)


def export_json(project_task_map):
    try:
        with open('reports/export.json', 'x') as f:
            json.dump(project_task_map, f, indent=4, sort_keys=True)
    except FileExistsError:
        with open('reports/export.json', 'w') as f:
            json.dump(project_task_map, f, indent=4, sort_keys=True)


def main(argv):
    project_name = ""
    projects = {}
    maniphest_tasks = {}
    maniphest_task_ids = []
    task_transaction_map = {}

    try:
        opts, args = getopt.getopt(argv, "hp:t:", ["project=", "task="])
    except getopt.GetoptError:
        print_help()
        phabricator.session.close()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print_help()
            phabricator.session.close()
            sys.exit()
        elif opt in ("-p", "--project"):
            project_name = arg
        elif opt in ("-t", "--task"):
            maniphest_tasks = arg
            if maniphest_tasks is not None and str(maniphest_tasks).strip() != '':
                maniphest_task_ids = str(maniphest_tasks).split(',')
    print("Project name provided:", project_name)
    print("Fetching project task details ...")

    conduit = phabricator.conduit
    if project_name is not None and project_name != '':
        try:
            project_response = conduit.Project.search(conduit.Project(), project_name)
            project_details = project_response['result']['data']
        except Exception as e:
            print("Error parsing project response:", repr(e))
            phabricator.session.close()
            sys.exit(2)

        if project_details is None or type(project_details) != list:
            print('Unexpected response', project_details)
            phabricator.session.close()
            sys.exit(2)

        for project_detail in project_details:
            projects[project_detail['phid']] = {'details': project_detail}
            try:
                project_maniphest_tasks_response = conduit.Maniphest.query(conduit.Maniphest(), project_detail['phid'])
                project_maniphest_tasks_details = project_maniphest_tasks_response['result']
            except Exception as e:
                print("Error parsing maniphest task response:", repr(e))
                phabricator.session.close()
                sys.exit(2)
            if project_maniphest_tasks_details is None or type(project_maniphest_tasks_details) != dict:
                print('Unexpected response', project_maniphest_tasks_details)
                phabricator.session.close()
                sys.exit(2)

            for maniphest_task_details in dict(project_maniphest_tasks_details).values():
                maniphest_task_ids.append(maniphest_task_details['id'])
                if maniphest_task_details['id'] not in maniphest_tasks:
                    maniphest_tasks[maniphest_task_details['id']] = {'details': maniphest_task_details}
            task_ids_to_be_queried = {}
            for i in range(len(maniphest_task_ids)):
                current_key = 'ids[' + str(i) + ']'
                task_ids_to_be_queried[current_key] = maniphest_task_ids[i]
            if task_ids_to_be_queried is None or len(task_ids_to_be_queried) == 0:
                print('No Tasks in project', project_maniphest_tasks_details)
                phabricator.session.close()
                sys.exit(2)
            try:
                task_transaction_response = conduit.Maniphest.get_transactions(conduit.Maniphest(), task_ids_to_be_queried)
                task_transaction_details = task_transaction_response['result']
            except Exception as e:
                print("Error parsing task transaction response:", repr(e))
                phabricator.session.close()
                sys.exit(2)
            if task_transaction_details is None or type(task_transaction_details) != dict or len(task_transaction_details) == 0:
                print('No transaction response in any tasks', task_transaction_details)
                phabricator.session.close()
                sys.exit(2)
            for maniphest_task_id, task_transaction_list in dict(task_transaction_details).items():
                revisions_tagged = []
                status_updates = []
                differential_revisions_map = {}
                revision_inlinecomments_map = {}
                revision_phids_to_be_queried = {}
                for task_transaction_detail in task_transaction_list:
                    if task_transaction_detail is not None and type(task_transaction_detail) == dict \
                            and task_transaction_detail['transactionType'] in ['core:edge', 'status', 'core:subtype']:
                        if task_transaction_detail['transactionType'] == 'core:edge':
                            task_edges = task_transaction_detail['newValue']
                            if task_edges is not None and type(task_edges) == list:
                                for task_edge in task_edges:
                                    if str(task_edge) != '' and str(task_edge).startswith('PHID-DREV-') and task_edge not in revisions_tagged:
                                        revisions_tagged.append(task_edge)
                        elif task_transaction_detail['transactionType'] == 'status':
                            status_updates.append(task_transaction_detail)
                        elif task_transaction_detail['transactionType'] == 'core:subtype' and maniphest_task_id in maniphest_tasks and "subtype" not in maniphest_tasks[maniphest_task_id]['details']:
                            maniphest_tasks[maniphest_task_id]['details']['subtype'] = task_transaction_detail['newValue']

                for i in range(len(revisions_tagged)):
                    current_key = 'constraints[phids][' + str(i) + ']'
                    revision_phids_to_be_queried[current_key] = revisions_tagged[i]
                if revision_phids_to_be_queried is not None and len(revision_phids_to_be_queried) > 0:
                    differential_revisions_details = None
                    try:
                        differential_revision_response = conduit.Differential.search_revisions(conduit.Differential(), revision_phids_to_be_queried)
                        differential_revisions_details = differential_revision_response['result']['data']
                    except Exception as e:
                        print("Error parsing differential revision response:", repr(e))

                    if differential_revisions_details is not None or type(differential_revisions_details) == list:

                        for differential_revision_details in list(differential_revisions_details):
                            if differential_revision_details is not None and type(differential_revision_details) == dict:
                                differential_revision_details = dict(differential_revision_details)
                                if 'fields' in differential_revision_details and differential_revision_details['fields'] is not None:
                                    if 'status' in differential_revision_details['fields'] \
                                            and differential_revision_details['fields']['status'] is not None \
                                            and differential_revision_details['fields']['status']['value'] != 'abandoned':
                                        revision_id = 'D' + str(differential_revision_details['id'])
                                        if revision_id not in differential_revisions_map:
                                            differential_revisions_map[revision_id] = differential_revision_details

                        for revision_id in differential_revisions_map.keys():
                            if revision_id not in revision_inlinecomments_map:
                                revision_inlinecomments_count = 0
                                revision_inlinecomments_done_count = 0
                                revision_comments_author_map = {}
                                dummy_comments = ["", "OK", "OKAY", "OKK", "SURE", "FINE", "DONE", "HAN", "YES", "YEAH", "HAN", "NO", "NOPES", "NOPE", "NOT SURE"]
                                inline_comments_details = None
                                try:
                                    inline_comments_response = conduit.Transaction.search(conduit.Transaction(), revision_id)
                                    inline_comments_details = inline_comments_response['result']['data']
                                except Exception as e:
                                    print("Error parsing inline comments response:", repr(e))

                                if inline_comments_details is not None or type(inline_comments_details) == list:
                                    for inline_comment_details in list(inline_comments_details):
                                        if inline_comment_details is not None and type(inline_comment_details) == dict:
                                            inline_comment_details = dict(inline_comment_details)
                                            if "type" in inline_comment_details and inline_comment_details['type'] is not None \
                                                    and inline_comment_details['type'] == 'inline' \
                                                    and "fields" in inline_comment_details and inline_comment_details['fields'] is not None \
                                                    and "replyToCommentPHID" in inline_comment_details['fields'] \
                                                    and (inline_comment_details['fields']['replyToCommentPHID'] is None or inline_comment_details['fields']['replyToCommentPHID'] == "") \
                                                    and "comments" in inline_comment_details and inline_comment_details['comments'] is not None \
                                                    and type(inline_comment_details['comments']) == list:
                                                for inline_comment in list(inline_comment_details['comments']):
                                                    if inline_comment is not None and type(inline_comment) == dict:
                                                        inline_comment = dict(inline_comment)
                                                        if "removed" in inline_comment and inline_comment['removed'] is False \
                                                                and "content" in inline_comment and inline_comment['content'] is not None \
                                                                and "raw" in inline_comment['content'] and inline_comment['content']['raw'] is not None \
                                                                and str(inline_comment['content']['raw']).strip() != "" \
                                                                and str(inline_comment['content']['raw']).strip().upper() not in dummy_comments:
                                                            revision_inlinecomments_count += 1
                                                            if "authorPHID" in inline_comment and inline_comment['authorPHID'] is not None \
                                                                    and str(inline_comment['authorPHID']).strip() != "":
                                                                if inline_comment['authorPHID'] in revision_comments_author_map:
                                                                    revision_comments_author_map[inline_comment['authorPHID']] += 1
                                                                else:
                                                                    revision_comments_author_map[inline_comment['authorPHID']] = 1

                                                if "isDone" in inline_comment_details['fields'] and inline_comment_details['fields']['isDone'] is True:
                                                    revision_inlinecomments_done_count += 1
                                    revision_inlinecomments_map[revision_id] = {
                                        "count": revision_inlinecomments_count,
                                        "done": revision_inlinecomments_done_count,
                                        "author_wise_count": revision_comments_author_map
                                    }

                if maniphest_task_id not in task_transaction_map:
                    task_transaction_map[maniphest_task_id] = {
                        'statuses': status_updates,
                        'revisions': differential_revisions_map,
                        'comments': revision_inlinecomments_map
                    }
                maniphest_tasks[maniphest_task_id]['transactions'] = task_transaction_map[maniphest_task_id]

            projects[project_detail['phid']]['tasks'] = maniphest_tasks
            print("Exporting report as json with raw data ...")
            export_json(projects)
            print("Exporting csv report from raw json dump ...")
            construct_csv()


if __name__ == '__main__':
    if config.CONDUIT_TOKEN == "" or config.PHABRICATOR_HOST == "" or not config.CONDUIT_TOKEN.startswith("api-"):
        print("Phabricator host url or conduit api token not provided or not correct. Please update config.py")
        sys.exit(2)

    main(sys.argv[1:])
    phabricator.session.close()
