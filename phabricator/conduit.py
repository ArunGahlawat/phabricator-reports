import config,urllib.parse,sys,phabricator,json


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
            'constraints[name]':project_name,
            'limit': '100'
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
        data['limit'] = '100'
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
            'projectPHIDs[0]': project_name,
            'limit': '100'
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


class Transaction:
    def __init__(self):
        self.search_endpoint = "/api/transaction.search"
        self.headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

    def search(self,revision_id):
        data = {
            'api.token': config.CONDUIT_TOKEN,
            'objectIdentifier':revision_id,
            'limit': '100'
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


class User:
    def __init__(self):
        self.search_endpoint = "/api/user.search"
        self.headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

    def search(self,user_dict):
        data = user_dict
        data['api.token'] = config.CONDUIT_TOKEN
        data['limit'] = '100'
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

    def get_user_details(self,user_phid):
        user_details = {}
        with open("cache/user_map.json",'r') as f:
            user_details = json.load(f)
        if user_details is not None and issubclass(type(user_details),dict) and len(dict(user_details)) > 0 and user_phid in dict(user_details):
            return dict(user_details)[user_phid]
        else:
            user_dict = {}
            current_key = 'constraints[phids][0]'
            user_dict[current_key] = user_phid
            user_search_details = None
            try:
                user_search_response = self.search(user_dict)
                user_search_details = user_search_response['result']['data']
            except Exception as e:
                print("Couldn't fetch user details:",repr(e))
                return ""
            if user_search_details is not None or type(user_search_details) == list:
                for user_details_queried in list(user_search_details):
                    if type(user_details_queried) == dict and "fields" in user_details_queried \
                            and "username" in dict(user_details_queried)['fields'] and dict(user_details_queried)['fields']['username'] is not None:
                        user_details[user_details_queried['phid']] = {
                            'username': user_details_queried['fields']['username'],
                            'realName': user_details_queried['fields']['realName']
                        }
                        with open("cache/user_map.json",'w') as f:
                            json.dump(user_details, f, indent=4, sort_keys=True)
                        return user_details[user_phid]






