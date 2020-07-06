import sys,getopt, config, requests, phabricator.conduit


def print_help():
    print('generate_report.py -p <project name> -t <task id>')
    print('or generate_report.py --project <project name> --task <task id>')
    print('Either project name is required')
    print('Eg. generate_report.py -p "This is project name"')
    print('Eg. generate_report.py -t "T1234')
    print('Eg. generate_report.py -p "This is project name" -t "T1234')
    print('Eg. generate_report.py --project "This is project name" --task "T1234')
    print("generate_report.py -h for usage help")


def main(argv):
    project_name = ""
    projects = {}
    maniphest_tasks = {}
    maniphest_task_ids = []
    project_task_map = {}
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
        project_response = conduit.Project.search(conduit.Project(),project_name)
        project_details = project_response['result']['data']
        if project_details is None or type(project_details) != list:
            print('Unexpected response',project_details)
            phabricator.session.close()
            sys.exit(2)

        for project_detail in project_details:
            projects[project_detail['phid']] = project_detail
            project_maniphest_tasks_response = conduit.Maniphest.query(conduit.Maniphest(),project_detail['phid'])
            project_maniphest_tasks_details = project_maniphest_tasks_response['result']
            if project_maniphest_tasks_details is None or type(project_maniphest_tasks_details) != dict:
                print('Unexpected response', project_maniphest_tasks_details)
                phabricator.session.close()
                sys.exit(2)

            for maniphest_task_phid, maniphest_task_details in dict(project_maniphest_tasks_details).items():
                maniphest_task_ids.append(maniphest_task_details['id'])
                if maniphest_task_details['id'] not in maniphest_tasks:
                    maniphest_tasks[maniphest_task_details['id']]['details'] = maniphest_task_details
                task_ids_to_be_queried = {}
                for i in range(len(maniphest_task_ids)):
                    current_key = 'ids['+str(i)+']'
                    task_ids_to_be_queried[current_key] = maniphest_task_ids[i]
                task_transaction_response = conduit.Maniphest.get_transactions(conduit.Maniphest(),task_ids_to_be_queried)
                task_transaction_details = task_transaction_response['result']
                if task_transaction_details is None or type(task_transaction_details) != dict:
                    print('Unexpected response', task_transaction_details)
                    phabricator.session.close()
                    sys.exit(2)
                status_updates = []
                revisions_tagged = []
                for task_transaction_detail in dict(task_transaction_details).values():
                    if task_transaction_detail is not None and type(task_transaction_detail) == dict \
                            and task_transaction_detail['transactionType'] in ['core:edge','status']:
                        if task_transaction_detail['transactionType'] == 'core:edge':
                            task_edges = task_transaction_detail['newValue']
                            if task_edges is not None and type(task_edges) == list:
                                for task_edge in task_edges:
                                    if str(task_edge) != '' and str(task_edge).startswith('PHID-DREV-'):
                                        revisions_tagged.append(task_edge)
                        elif task_transaction_detail['transactionType'] == 'status':
                            status_updates.append(task_transaction_detail)
                revision_phids_to_be_queried = {}
                for i in range(len(revisions_tagged)):
                    current_key = 'constraints[phids][' + str(i) + ']'
                    revision_phids_to_be_queried[current_key] = revisions_tagged[i]
                differential_revision_response = conduit.Differential.search_revisions(conduit.Differential(), revision_phids_to_be_queried)
                differential_revisions_details = differential_revision_response['result']['data']
                if differential_revisions_details is None or type(differential_revisions_details) != list:
                    print('Unexpected response', differential_revisions_details)
                    phabricator.session.close()
                    sys.exit(2)

                differential_revisions_map = {}
                for differential_revision_details in list(differential_revisions_details):
                    if differential_revision_details is not None and type(differential_revision_details) == dict:
                        differential_revision_details = dict(differential_revision_details)
                        if 'fields' in differential_revision_details and differential_revision_details['fields'] is not None:
                            if 'status' in differential_revision_details['fields'] \
                                    and differential_revision_details['fields']['status'] is not None \
                                    and differential_revision_details['fields']['status']['value'] != 'abandoned':
                                revision_id = 'D'+differential_revision_details['id']
                                if revision_id not in differential_revisions_map:
                                    differential_revisions_map[revision_id] = differential_revision_details

                if maniphest_task_details['id'] not in task_transaction_map:
                    task_transaction_map[maniphest_task_details['id']] = {
                        'statuses': status_updates,
                        'revisions': differential_revisions_map
                    }









            if project_detail['phid'] not in project_task_map:
                project_task_map[project_detail['phid']] = maniphest_tasks







if __name__ == '__main__':
    if config.CONDUIT_TOKEN == "" or config.PHABRICATOR_HOST == "" or not config.CONDUIT_TOKEN.startswith("api-"):
        print("Phabricator host url or conduit api token not provided or not correct. Please update config.py")
        sys.exit(2)

    main(sys.argv[1:])

