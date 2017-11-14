import os
import requests
import urls
from re import search
import boto3

from botocore.exceptions import ClientError

from ConfigParser import SafeConfigParser

from .exceptions import ConfigurationException


class EpicJob(object):
    pass


class EpicDataLocation(object):
    pass


class EpicClient(object):
    """Client for the EPIC API"""

    def __init__(self, epic_url=None, epic_token=None, config_file=None):
        super(EpicClient, self).__init__()
        self._load_config(epic_url, epic_token, config_file)
        self._check_config()

    def _get_request_headers(self):
        if self.EPIC_TOKEN is not None and len(self.EPIC_TOKEN) > 0:
            headers = {'Authorization': "Token " + self.EPIC_TOKEN}
        else:
            headers = {}
        if self.EPIC_TEAM != 0:
            headers['X-EPIC-TEAM'] = str(self.EPIC_TEAM)
        if self.EPIC_PROJECT != 0:
            headers['X-EPIC-PROJECTCODE'] = str(self.EPIC_PROJECT)
        return headers

    def _get_request(self, url, params=None):
        print(self._get_request_headers())
        r = requests.get(url=self.EPIC_API_URL + url,
                         headers=self._get_request_headers(), params=params)
        if r.status_code not in range(200, 299):
            raise exceptions.ResponseError(r.text)
        else:
            try:
                return r.json()
            except ValueError:
                return "No Response"

    def _post_request(self, url, params, headers=None):
        if headers is None:
            headers = self._get_request_headers()
        r = requests.post(
            json=params, url=self.EPIC_API_URL + url, headers=headers)
        if r.status_code not in range(200, 299):
            raise exceptions.ResponseError(r.text)
        else:
            try:
                return r.json()
            except ValueError:
                return "No Response"

    def _create_boto_client():
        creds = get_request('/accounts/aws/get/', get_request_headers())
        client = boto3.resource('s3',
                                aws_access_key_id=creds['aws_key_id'],
                                aws_secret_access_key=creds['aws_secret_key'])
        arn = get_request('/data/aws/get', get_request_headers())
        print(arn)
        try:
            bucket = search(r'[a-z-]+/', arn).group(0).rstrip('/')
            prefix = search(r'\d{2,}', arn.lstrip('arn:aws:s3:::')).group(0)
            print(bucket, key)
        except IndexError as e:
            print("Bucket Error: " + e.message)
            return
        return {'client': client, 'bucket': bucket, 'key': key}

    def get_s3_information(self):
        headers = self._get_request_headers()
        arn = self._get_request(urls.DATA_LOCATION)
        try:
            bucket = search(r'[a-z-]+/', arn).group(0).rstrip('/')
            prefix = search(r'\d{2,}', arn.lstrip('arn:aws:s3:::')).group(0)
        except IndexError as e:
            raise exceptions.ResponseError("Bucket Error: " + e.message)
        return {'bucket': bucket, 'prefix': prefix, 'arn': arn}

    def get_aws_credentials(self):
        headers = self._get_request_headers()
        return self._get_request(urls.ACCOUNT_CREDENTIALS)

    def _load_config(self, epic_url=None, epic_token=None, config_file=None):
        """
        Load client config, order of precedence = args > config_file > env 
        """
        self.EPIC_API_URL = os.environ.get('EPIC_API_ENDPOINT', None)
        self.EPIC_TOKEN = os.environ.get('EPIC_TOKEN', None)
        self.EPIC_TEAM = os.environ.get('EPIC_TEAM', 0)
        self.EPIC_PROJECT = os.environ.get('EPIC_PROJECT', 0)
        if config_file is not None:
            self._load_config_file(config_file)
        if epic_url is not None:
            self.EPIC_API_URL = epic_url
        if epic_token is not None:
            self.EPIC_TOKEN = epic_token

    def _check_config(self):
        if self.EPIC_API_URL is None:
            raise ConfigurationException(
                "Missing EPIC URL, set EPIC_API_URL or supply a configuration file")
        elif self.EPIC_TOKEN is None:
            raise ConfigurationException(
                "Missing EPIC URL, set EPIC_TOKEN or supply a configuration file")

    def _load_config_file(self, file):
        parser = SafeConfigParser(allow_no_value=True)
        if os.path.isfile(file):
            parser.read(file)
            if parser.has_section('epic'):
                self.EPIC_API_URL = parser.get('epic', 'url')
                self.EPIC_TOKEN = parser.get('epic', 'token')
                self.EPIC_TEAM = parser.getint('epic', 'default_team')
                self.EPIC_PROJECT = parser.getint('epic', 'default_project')
        else:
            raise ConfigurationException(
                "Invalid EPIC configuration file %s" % file)

    def get_security_token(self, username, password):
        params = {'username': username, 'password': password}
        return self._post_request(urls.AUTH, params, headers="")['token']

    def list_project_codes(self):
        response = self._get_request(urls.PROJECTS_LIST)
        return response

    def list_user_notifications(self):
        pass

    def delete_user_notification(self):
        pass

    def get_aws_tokens():
        pass

    def create_aws_tokens():
        pass

    def list_teams(self):
        return self._get_request(urls.TEAMS_LIST)

    def create_team():
        pass

    def get_s3_location():
        pass

    def list_data_locations(self, filepath):
        if filepath is not None:
            params = {'dir': filepath}
        else:
            params = None
        return self._get_request(urls.DATA_LIST, params)

    def delete_file():
        pass

    def upload_file(self, source, destination, dryrun=False):
        creds = self.get_aws_credentials()
        bucket = self.get_s3_information()
        s3 = boto3.resource('s3',
                            aws_access_key_id=creds['aws_key_id'],
                            aws_secret_access_key=creds['aws_secret_key'])
        if not dryrun:
            s3.Bucket(bucket['bucket']).upload_file(
                source, os.path.join(bucket['prefix'], destination))

    def download_file(self, source, destination, status_callback=None, dryrun=False):
        creds = self.get_aws_credentials()
        bucket = self.get_s3_information()
        s3 = boto3.resource('s3',
                            aws_access_key_id=creds['aws_key_id'],
                            aws_secret_access_key=creds['aws_secret_key'])
        if status_callback is not None:
            status_callback('Downloading %s to %s %s' % (os.path.join(
                bucket['prefix'], source), destination, "(dryrun)" if dryrun else ""))
        if not dryrun:
            s3.Bucket(bucket['bucket']).download_file(
                os.path.join(bucket['prefix'], source), destination)

    def download_fileobj(self, source, destination_obj, status_callback = None, dryrun = False):
        creds = self.get_aws_credentials()
        bucket = self.get_s3_information()
        s3 = boto3.resource('s3',
                            aws_access_key_id=creds['aws_key_id'],
                            aws_secret_access_key=creds['aws_secret_key'])
        if status_callback is not None:
            status_callback('Downloading %s to object %s' % (os.path.join(bucket['prefix'], source), "(dryrun)" if dryrun else ""))
        if not dryrun:
            s3.Bucket(bucket['bucket']).download_fileobj(os.path.join(bucket['prefix'], source), destination_obj)

    def upload_directory(self, source_dir, destination_prefix, rel_to='.', status_callback=None, dryrun=False):
        creds = self.get_aws_credentials()
        bucket = self.get_s3_information()
        s3 = boto3.resource('s3',
                            aws_access_key_id=creds['aws_key_id'],
                            aws_secret_access_key=creds['aws_secret_key'])
        for root, dirs, files in os.walk(source_dir):
            for filename in files:
                local_path = os.path.join(root, filename)
                relative_path = os.path.relpath(local_path, rel_to)
                s3_path = os.path.join(bucket['bucket'], bucket[
                                       'prefix'], destination_prefix, relative_path)
                key = os.path.join(
                    bucket['prefix'], destination_prefix.strip("/"), relative_path)
                try:
                    s3.Object(bucket['bucket'], key).load()
                    if status_callback is not None:
                        status_callback('File found in data store, skipping %s %s' % (
                            key, "(dryrun)" if dryrun else ""))
                except ClientError as e:
                    if status_callback is not None:
                        status_callback("Uploading %s %s" % (os.path.join(bucket['prefix'], destination_prefix, relative_path),
                                                             "(dryrun)" if dryrun else ""))
                    if not dryrun:
                        s3.Bucket(bucket['bucket']).upload_file(
                            local_path, key)

    def download_directory(self, source, destination, status_callback=None, dryrun=False):
        creds = self.get_aws_credentials()
        bucket = self.get_s3_information()
        s3 = boto3.resource('s3',
                            aws_access_key_id=creds['aws_key_id'],
                            aws_secret_access_key=creds['aws_secret_key'])
        for obj in s3.Bucket(bucket['bucket']).objects.filter(Prefix=bucket['prefix'] + source):
            filename = os.path.join(destination, obj.key.split("/", 1)[1])
            if status_callback is not None:
                status_callback("Downloading %s to %s %s" % (
                    obj.key, filename, "(dryrun)" if dryrun else ""))
            if not dryrun:
                path, file_n = os.path.split(filename)
                try:
                    os.makedirs(path)
                except OSError:
                    pass
                try:
                    s3.Bucket(bucket['bucket']).download_file(
                        obj.key, filename)
                except botocore.exceptions.ClientError as e:
                    print e

    def move_file():
        pass

    def list_job_status(self):
        return self._get_request(urls.BATCH_JOB_LIST)

    def get_job_status(self, job_id):
        return self._get_request(urls.BATCH_JOB_STATUS + str(job_id))

    def list_queue_status(self):
        return self._get_request(urls.BATCH_QUEUES)

    def get_job_costs(self, job_definition={}):
        return self._post_request(urls.BATCH_JOB_COST, job_definition)

    def create_job(self, job_definition={}):
        return self._post_request(urls.BATCH_JOB_CREATE, job_definition)

    def cancel_job():
        pass

    def list_clusters():
        pass

    def delete_job():
        pass

    def list_applications(self):
        return self._get_request(urls.BATCH_APPLICATIONS)

    def list_application_versions(self, app_id):
        return self._get_request(urls.application_version(app_id))
