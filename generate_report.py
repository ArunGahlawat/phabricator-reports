import sys,getopt, config, requests, phabricator.conduit, json


def print_help():
    print('generate_report.py -p <project name> -t <task id>')
    print('or generate_report.py --project <project name> --task <task id>')
    print('Either project name is required')
    print('Eg. generate_report.py -p "This is project name"')
    print('Eg. generate_report.py -t "T1234')
    print('Eg. generate_report.py -p "This is project name" -t "T1234')
    print('Eg. generate_report.py --project "This is project name" --task "T1234')
    print("generate_report.py -h for usage help")


def construct_csv(project_task_map):
    with open('reports/export.json', 'w') as f:
        json.dump(project_task_map, f, indent=4, sort_keys=True)


def main(argv):
    project_name = ""
    projects = {}
    maniphest_tasks = {}
    maniphest_task_ids = []
    task_transaction_map = {}

    try:
        opts, args = getopt.getopt(argv,"hp:t:",["project=","task="])
    except getopt.GetoptError:
        print_help()
        phabricator.session.close()
        sys.exit(2)
    for opt,arg in  opts:
        if opt == '-h':
            print_help()
            phabricator.session.close()
            sys.exit()
        elif opt in ("-p","--project"):
            project_name = arg
        elif opt in ("-t","--task"):
            maniphest_tasks = arg
            if maniphest_tasks is not None and str(maniphest_tasks).strip() != '':
                maniphest_task_ids = str(maniphest_tasks).split(',')
    print("Project name provided:", project_name)
    print("Task id provided:", maniphest_task_ids)
    conduit = phabricator.conduit
    if project_name is not None and project_name != '':
        try:
            project_response = conduit.Project.search(conduit.Project(), project_name)
            project_details = project_response['result']['data']
        except Exception as e:
            print("Error parsing project response:",repr(e))
            phabricator.session.close()
            sys.exit(2)

        if project_details is None or type(project_details) != list:
            print('Unexpected response',project_details)
            phabricator.session.close()
            sys.exit(2)

        for project_detail in project_details:
            projects[project_detail['phid']] = {'details':project_detail}
            try:
                project_maniphest_tasks_response = conduit.Maniphest.query(conduit.Maniphest(),project_detail['phid'])
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
                current_key = 'ids['+str(i)+']'
                task_ids_to_be_queried[current_key] = maniphest_task_ids[i]
            if task_ids_to_be_queried is None or len(task_ids_to_be_queried) == 0:
                print('No Tasks in project', project_maniphest_tasks_details)
                phabricator.session.close()
                sys.exit(2)
            try:
                task_transaction_response = conduit.Maniphest.get_transactions(conduit.Maniphest(),task_ids_to_be_queried)
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
                            and task_transaction_detail['transactionType'] in ['core:edge','status']:
                        if task_transaction_detail['transactionType'] == 'core:edge':
                            task_edges = task_transaction_detail['newValue']
                            if task_edges is not None and type(task_edges) == list:
                                for task_edge in task_edges:
                                    if str(task_edge) != '' and str(task_edge).startswith('PHID-DREV-') and task_edge not in revisions_tagged:
                                        revisions_tagged.append(task_edge)
                        elif task_transaction_detail['transactionType'] == 'status':
                            status_updates.append(task_transaction_detail)

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
                                        revision_id = 'D'+str(differential_revision_details['id'])
                                        if revision_id not in differential_revisions_map:
                                            differential_revisions_map[revision_id] = differential_revision_details

                        for revision_id in differential_revisions_map.keys():
                            if revision_id not in revision_inlinecomments_map:
                                revision_inlinecomments_count = 0
                                revision_inlinecomments_done_count = 0
                                revision_comments_author_map = {}
                                dummy_comments = ["","OK","OKAY","OKK","SURE","FINE","DONE","HAN","YES","YEAH","HAN","NO","NOPES","NOPE","NOT SURE"]
                                inline_comments_details = None
                                try:
                                    inline_comments_response = conduit.Transaction.search(conduit.Transaction(),revision_id)
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
                                                        if "removed" in inline_comment and inline_comment['removed'] == False \
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

                                                if "isDone" in inline_comment_details['fields'] and inline_comment_details['fields']['isDone'] == True:
                                                    revision_inlinecomments_done_count += 1
                                    revision_inlinecomments_map[revision_id] = {
                                        "count":revision_inlinecomments_count,
                                        "done":revision_inlinecomments_done_count,
                                        "author_wise_count":revision_comments_author_map
                                    }

                if maniphest_task_id not in task_transaction_map:
                    task_transaction_map[maniphest_task_id] = {
                        'statuses': status_updates,
                        'revisions': differential_revisions_map,
                        'comments':revision_inlinecomments_map
                    }
                maniphest_tasks[maniphest_task_id]['transactions'] = task_transaction_map[maniphest_task_id]

            projects[project_detail['phid']]['tasks'] = maniphest_tasks
            construct_csv(projects)


if __name__ == '__main__':
    if config.CONDUIT_TOKEN == "" or config.PHABRICATOR_HOST == "" or not config.CONDUIT_TOKEN.startswith("api-"):
        print("Phabricator host url or conduit api token not provided or not correct. Please update config.py")
        sys.exit(2)

    main(sys.argv[1:])
    phabricator.session.close()

