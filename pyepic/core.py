import os
import requests
import urls
from re import search
import boto3
import botocore
import errno
import datetime
import pytz

from botocore.exceptions import ClientError

from ConfigParser import SafeConfigParser, RawConfigParser

from .exceptions import (
    ConfigurationException,
    CommandError,
    ResponseError
)


class EPICPath(object):

    def __init__(self, bucket, prefix, path, filename=None):
        self.protocol = "epic://"
        self.bucket = bucket
        self.prefix = prefix
        if path.startswith(self.protocol):
            self.path = path[len(self.protocol):]
        else:
            self.path = path
        if self.path.endswith(os.sep):
            self.path = self.path[:-1]
        self.filename = filename

    def get_s3_key(self):
        if self.filename:
            return self.prefix + '/' + self.path + '/' + self.filename
        else:
            return self.prefix + '/' + self.path

    def get_user_string(self):
        if self.filename:
            return self.protocol + self.path + '/' + self.filename
        else:
            return self.protocol + self.path

    def get_local_path(self):
        if self.filename:
            return self.path.replace('/', os.sep) + os.sep + self.filename
        else:
            return self.path.replace('/', os.sep)


class EpicConfigFile(object):
    def __init__(self, config_file):
        self.EPIC_API_URL = None
        self.EPIC_TOKEN = None
        self.EPIC_TEAM = None
        self.EPIC_PROJECT = None
        self._load_config(config_file)

    def _load_config(self, configfile):
        parser = SafeConfigParser(allow_no_value=True)
        if os.path.isfile(configfile):
            parser.read(configfile)
            if parser.has_section('epic'):
                self.EPIC_API_URL = parser.get('epic', 'url')
                self.EPIC_TOKEN = parser.get('epic', 'token')
                self.EPIC_TEAM = parser.getint('epic', 'default_team')
                self.EPIC_PROJECT = parser.getint('epic', 'default_project')
        else:
            raise ConfigurationException(
                "Invalid EPIC configuration file %s" % configfile)


class EpicClient(object):
    """Client for the EPIC API"""

    def __init__(self, epic_url, epic_token, epic_team=0, epic_project=0):
        super(EpicClient, self).__init__()
        self._s3_resource = None
        self._s3_client = None
        self._s3_info = None
        self.EPIC_API_URL = epic_url
        self.EPIC_TOKEN = epic_token
        self.EPIC_TEAM = epic_team
        self.EPIC_PROJECT = epic_project
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
        r = requests.get(url=self.EPIC_API_URL + url,
                         headers=self._get_request_headers(), params=params)
        if r.status_code not in range(200, 299):
            raise ResponseError(r.text)
        else:
            try:
                return r.json()
            except ValueError:
                return "No Response"

    def _post_request(self, url, params={}, headers=None):
        if headers is None:
            headers = self._get_request_headers()
        r = requests.post(
            json=params, url=self.EPIC_API_URL + url, headers=headers)
        if r.status_code not in range(200, 299):
            raise ResponseError(r.text)
        else:
            try:
                return r.json()
            except ValueError:
                return "No Response"

    def _create_boto_client(self):
        creds = self.get_or_create_aws_tokens()
        self._s3_resource = boto3.resource('s3',
                                           aws_access_key_id=creds['aws_key_id'],
                                           aws_secret_access_key=creds['aws_secret_key'])
        self._s3_client = boto3.client('s3',
                                       aws_access_key_id=creds['aws_key_id'],
                                       aws_secret_access_key=creds['aws_secret_key'])
        self._s3_info = self.get_s3_information()

    def get_s3_information(self):
        if self._s3_info:
            return self._s3_info
        arn = self._get_request(urls.DATA_LOCATION)
        try:
            bucket = search(r'[a-z-]+/', arn).group(0).rstrip('/')
            prefix = search(r'\d{2,}', arn.lstrip('arn:aws:s3:::')).group(0)
        except IndexError as e:
            raise ResponseError("Bucket Error: " + e.message)
        return {'bucket': bucket, 'prefix': prefix, 'arn': arn}

    def get_aws_tokens(self):
        response = self._get_request(urls.AWS_GET)
        return response

    def get_or_create_aws_tokens(self):
        response = self._post_request(urls.AWS_CREATE)
        return response

    def _check_config(self):
        if self.EPIC_API_URL is None:
            raise ConfigurationException(
                "Missing EPIC URL, set EPIC_API_ENDPOINT or supply a configuration file")
        elif self.EPIC_TOKEN is None:
            raise ConfigurationException(
                "Missing EPIC API TOKEN, set EPIC_TOKEN or supply a configuration file")

    def write_config_file(self, file=None):
        output_file = file if file is not None else self._config_file
        if output_file is None:
            raise ConfigurationException("Valid config file not specified for write_config_file")
        config = RawConfigParser()
        config.add_section('epic')
        config.set('epic', 'url', self.EPIC_API_URL)
        config.set('epic', 'token', self.EPIC_TOKEN)
        config.set('epic', 'default_team', self.EPIC_TEAM)
        config.set('epic', 'default_project', self.EPIC_PROJECT)
        config_file = os.path.expanduser(output_file)
        try:
            os.makedirs(os.path.dirname(config_file))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        with open(config_file, 'wb') as configfile:
            config.write(configfile)

    def get_security_token(self, username, password):
        params = {'username': username, 'password': password}
        return self._post_request(urls.AUTH, params, headers="")['token']

    def list_project_codes(self):
        response = self._get_request(urls.PROJECTS_LIST)
        return response

    def list_teams(self):
        return self._get_request(urls.TEAMS_LIST)

    def get_s3_location(self):
        return self._get_request(urls.AWS_DATA_GET)

    @property
    def s3(self):
        if self._s3_resource is None:
            self._create_boto_client()
        return self._s3_resource

    @property
    def s3_client(self):
        if self._s3_client is None:
            self._create_boto_client()
        return self._s3_client

    def list_data_locations(self, filepath):
        if filepath is not None:
            if filepath.startswith('epic://'):
                filepath = filepath[7:]
            params = {'dir': filepath}
        else:
            params = None
        return self._get_request(urls.DATA_LIST, params)

    def get_key_info(self, key):
        s3_info = self.get_s3_information()
        try:
            return self.s3_client.head_object(Bucket=s3_info['bucket'], Key=key)
        except botocore.exceptions.ClientError as e:
            return None

    def delete_file(self, file, dryrun):
        s3_info = self.get_s3_information()
        if not file.startswith("epic://"):
            raise CommandError("PATH must be an EPIC Path")
        file = EPICPath(s3_info['bucket'], s3_info['prefix'], file.split("/", 1)[1])
        if dryrun:
                print("Deleting {} (dryrun)".format(file.get_user_string()))
        else:
            print("Deleting {}".format(file.get_user_string()))
            self.s3_client.delete_object(Bucket=s3_info['bucket'], Key=file.get_s3_key())

    def delete_folder(self, folder, dryrun):
        s3_info = self.get_s3_information()
        if not source.startswith("epic://"):
            raise CommandError("PATH must be an EPIC Path")
        source_prefix = source[6:]
        for file in self.list_epic_path(source_prefix):
            epath = EPICPath(s3_info['bucket'], s3_info['prefix'], file['key'].split("/", 1)[1])
            if dryrun:
                print("Deleting {} (dryrun)".format(epath.get_user_string()))
            else:
                print("Deleting {}".format(epath.get_user_string()))
                self.s3_client.delete_object(Bucket=s3_info['bucket'], Key=epath.get_s3_key())

    def _upload_file(self, bucket, source_file, destination_key):
        self.s3_client.upload_file(source_file, bucket, destination_key)

    def upload_file(self, source, destination, dryrun=False):
        s3_info = self.get_s3_information()
        if not destination.startswith("epic://"):
            raise CommandError("DESTINATION must be an EPIC Path")
        else:
            destination = EPICPath(s3_info['bucket'], s3_info['prefix'], destination, filename=os.path.basename(source))
            if dryrun:
                print("Uploading {} to {} (dryrun)".format(source, destination.get_user_string()))
            else:
                print("Uploading {} to {}".format(source, destination.get_user_string()))
                self.s3.Bucket(s3_info['bucket']).upload_file(
                    source, destination.get_s3_key())

    def _download_file(self, bucket, source_key, destination):
        self.s3_client.download_file(bucket, source_key, destination)

    def download_file(self, source, destination, status_callback=None, dryrun=False):
        s3_info = self.get_s3_information()
        if not source.startswith("epic://"):
            raise CommandError("SOURCE must be an EPIC Path")
        source = EPICPath(s3_info['bucket'], s3_info['prefix'], os.path.dirname(source), os.path.basename(source))
        if dryrun:
                print("Downloading {} to {} (dryrun)".format(source.get_user_string(), destination))
        else:
            print("Downloading {} to {}".format(source.get_user_string(), destination))
            try:
                os.makedirs(os.path.dirname(destination))
            except OSError:
                pass
            self.s3.Bucket(s3_info['bucket']).download_file(source.get_s3_key(), destination)

    def list_epic_path(self, path):
        s3_info = self.get_s3_information()
        key_list = []
        s3_prefix = s3_info['prefix'] + path
        for obj in self.s3.Bucket(s3_info['bucket']).objects.filter(Prefix=s3_info['prefix'] + path):
            key_list.append({'key': obj.key, 'last_modified': obj.last_modified, 'size': obj.size})
        return key_list

    def _copy_file(self, bucket, source_key, destination_key):
        """ Copy an object source_key to destination_key."""
        try:
            self.s3.Bucket(bucket).copy({'Bucket': bucket,
                                         'Key': source_key},
                                        destination_key)
        except ClientError as e:
            raise e

    def _s3_copy(self, source, destination, dryrun=False):
        # S3 to S3 sync
        source_prefix = source[6:]
        destination_prefix = destination[6:]
        for file in self.list_epic_path(source_prefix):
            source_key = file['key']
            dest_key = s3_info['prefix'] + destination_prefix + file['key'].split('/', 1)[1]
            existing_file = self.get_key_info(dest_key)
            if existing_file:
                if existing_file['LastModified'] >= file['last_modified']:
                    print("Skipping epic://{} as destination already exists".format(source_key))
                    continue
            if dryrun:
                print("Copy from epic://{} to epic://{} (dryrun)".format(source_key, dest_key))
            else:
                print("Copy from epic://{} to epic://{}".format(source_key, dest_key))
                self._copy_file(s3_info['bucket'], source_key, dest_key)

    def sync_folders(self, source, destination, dryrun=False):
        s3_info = self.get_s3_information()
        if source.startswith("epic://"):
            if destination.startswith("epic://"):
                self._s3_copy(source, destination, dryrun=dryrun)
            else:
                # EPIC to local sync
                source_prefix = source[6:]
                if os.path.isfile(destination):
                    raise CommandError("Destination cannot be a file")
                for file in self.list_epic_path(source_prefix):
                    epath = EPICPath(s3_info['bucket'], s3_info['prefix'], file['key'].split("/", 1)[1])
                    destination_file = os.path.join(destination, epath.get_local_path())
                    if os.path.isfile(destination_file):
                        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(destination_file), pytz.utc)
                        if mod_time >= file['last_modified']:
                            print("Skipping {} as destination already exists".format(epath.get_user_string()))
                            continue
                    if dryrun:
                        print("Copying from {} to {} (dryrun)".format(epath.get_user_string(), destination_file))
                    else:
                        print("Copying from {} to {}".format(epath.get_user_string(), destination_file))
                        if not os.path.exists(os.path.dirname(destination_file)):
                            os.makedirs(os.path.dirname(destination_file))
                        self._download_file(s3_info['bucket'], epath.get_s3_key(), str(destination_file))
        elif destination.startswith("epic://"):
            # Local to EPIC
            if os.path.isfile(source):
                raise CommandError("Source cannot be a file")
            local_files = []
            destination_prefix = destination[6:]
            for root, directory_path, files_path in os.walk(source):
                for file_path in files_path:
                    local_files.append(os.path.join(root, file_path))
            for file in local_files:
                epath = EPICPath(s3_info['bucket'], s3_info['prefix'], local_to_epic_path(file))
                existing_file = self.get_key_info(epath.get_s3_key())
                if existing_file:
                    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file), pytz.utc)
                    if existing_file['LastModified'] >= mod_time:
                        print("Skipping {} as destination already exists".format(file))
                        continue
                if dryrun:
                    print("Copying from {} to {} (dryrun)".format(file, epath.get_user_string()))
                else:
                    print("Copying from {} to {}".format(file, epath.get_user_string()))
                    self._upload_file(s3_info['bucket'], file, epath.get_s3_key())
        else:
            raise CommandError("Either SOURCE and/or DESTINATION must be an EPIC Path")

    def list_job_status(self):
        return self._get_request(urls.BATCH_JOB_LIST)

    def get_job_details(self, job_id):
        return self._get_request(urls.job_details(job_id))

    def list_queue_status(self):
        return self._get_request(urls.BATCH_QUEUES)

    def get_queue_details(self, queue_id):
        return self._get_request(urls.queue_details(queue_id))

    def cancel_job(self, job_id):
        self._post_request(urls.BATCH_JOB_CANCEL, {'pk': job_id})
        return self.get_job_details(job_id)

    def list_clusters(self, app_id, app_version_id):
        response = self._get_request(urls.CLUST_LIST + str(app_id) + '/' + str(app_version_id) + '/resources/')
        return response

    def list_applications(self):
        return self._get_request(urls.BATCH_APPLICATIONS)

    def list_application_versions(self, app_id):
        return self._get_request(urls.application_version(app_id))


def local_to_epic_path(localfile):
    if localfile.startswith('.{}'.format(os.sep)):
        return localfile[2:].replace(os.sep, '/')
    else:
        return localfile.replace(os.sep, '/')


def check_path_is_folder(path):
    if path == ".":
        return True
    if path.startswith("epic://"):
        return path.endswith('/')
    else:
        return path.endswith(os.sep)
