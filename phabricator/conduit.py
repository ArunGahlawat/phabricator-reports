import config,urllib.parse,sys,phabricator


class Common:
    @staticmethod
    def validate_conduit_response(response):
        if response is None or response.status_code != 200:
            print('Error fetching api response')
            return False
        response = response.json()
        if response is None or (response['error_info'] is not None and response['error_info'] != ''):
            print('Error in response:',response['error_info'])
            return False
        return True


class Project:
    def __init__(self):
        self.query_endpoint = "/api/project.query"
        self.search_endpoint = "/api/project.search"
        self.headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

    def search(self,project_name):
        data = {
            'api.token': config.CONDUIT_TOKEN,
            'constraints[name]':project_name
        }
        url = config.PHABRICATOR_HOST + self.search_endpoint
        data = urllib.parse.urlencode(data)
        try:
            response = phabricator.session.post(url,data=data,headers=self.headers)
        except Exception as e:
            print('Error in sending request',repr(e))
            phabricator.session.close()
            sys.exit(2)
        is_valid = Common.validate_conduit_response(response)
        if not is_valid:
            phabricator.session.close()
            sys.exit(2)
        return response.json()


class Differential:
    def __init__(self):
        self.search_endpoint = "/api/differential.revision.search"
        self.headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

    def search_revisions(self, revision_phid_dict):
        data = revision_phid_dict
        data['api.token'] = config.CONDUIT_TOKEN
        url = config.PHABRICATOR_HOST + self.search_endpoint
        data = urllib.parse.urlencode(data)
        try:
            response = phabricator.session.post(url, data=data, headers=self.headers)
        except Exception as e:
            print('Error in sending request', repr(e))
            phabricator.session.close()
            sys.exit(2)
        is_valid = Common.validate_conduit_response(response)
        if not is_valid:
            phabricator.session.close()
            sys.exit(2)
        return response.json()


class Maniphest:
    def __init__(self):
        self.query_endpoint = "/api/maniphest.query"
        self.gettasktransactions_endpoint = "/api/maniphest.gettasktransactions"
        self.headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

    def query(self,project_name):
        data = {
            'api.token': config.CONDUIT_TOKEN,
            'projectPHIDs[0]':project_name
        }
        url = config.PHABRICATOR_HOST + self.query_endpoint
        data = urllib.parse.urlencode(data)
        try:
            response = phabricator.session.post(url,data=data,headers=self.headers)
        except Exception as e:
            print('Error in sending request',repr(e))
            phabricator.session.close()
            sys.exit(2)
        is_valid = Common.validate_conduit_response(response)
        if not is_valid:
            phabricator.session.close()
            sys.exit(2)
        return response.json()

    def get_transactions(self,task_id_dict):
        data = task_id_dict
        data['api.token'] = config.CONDUIT_TOKEN
        url = config.PHABRICATOR_HOST + self.gettasktransactions_endpoint
        data = urllib.parse.urlencode(data)
        try:
            response = phabricator.session.post(url,data=data,headers=self.headers)
        except Exception as e:
            print('Error in sending request',repr(e))
            phabricator.session.close()
            sys.exit(2)
        is_valid = Common.validate_conduit_response(response)
        if not is_valid:
            phabricator.session.close()
            sys.exit(2)
        return response.json()

