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


class EpicJob(object):
    pass


class EpicDataLocation(object):
    pass


class EPICPath(object):

    def __init__(self, bucket, prefix, path, filename=None):
        self.protocol = "epic://"
        self.bucket = bucket
        self.prefix = prefix
        if path.startswith(self.protocol):
            self.path = path[len(self.protocol):]
        else:
            self.path = path
        if self.path.endswith("/"):
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


class EpicClient(object):
    """Client for the EPIC API"""

    def __init__(self, epic_url=None, epic_token=None, config_file=None):
        super(EpicClient, self).__init__()
        self._s3_resource = None
        self._s3_client = None
        self._s3_info = None
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

    def get_aws_credentials(self):
        return self._get_request(urls.ACCOUNT_CREDENTIALS)

    def _load_config(self, epic_url=None, epic_token=None, config_file=None):
        """
        Load client config, order of precedence = args > env > config_file
        """
        self.EPIC_API_URL = None
        self.EPIC_TOKEN = None
        self.EPIC_TEAM = 0
        self.EPIC_PROJECT = 0
        if config_file is not None:
            self._load_config_file(config_file)
            self._config_file = config_file
        self.EPIC_API_URL = os.environ.get('EPIC_API_ENDPOINT', self.EPIC_API_URL)
        self.EPIC_TOKEN = os.environ.get('EPIC_TOKEN', self.EPIC_TOKEN)
        self.EPIC_TEAM = int(os.environ.get('EPIC_TEAM', self.EPIC_TEAM))
        self.EPIC_PROJECT = int(os.environ.get('EPIC_PROJECT', self.EPIC_PROJECT))
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

    def list_user_notifications(self):
        response = self._get_request(urls.NOTIFICATIONS)
        return response

    def delete_user_notification(self):
        r = requests.delete(urls.NOTIFICATIONS,
                            headers=self._get_request_headers())
        if r.status_code != 200:
            raise ResponseError

    def get_aws_tokens(self):
        response = self._get_request(urls.AWS_GET)
        return response

    def get_or_create_aws_tokens(self):
        response = self._post_request(urls.AWS_CREATE)
        return response

    def create_aws_tokens(self):
        response = self._post_request(urls.AWS_CREATE)
        return response

    def list_teams(self):
        return self._get_request(urls.TEAMS_LIST)

    def create_team(self, team_specification={}):
        response = self._post_request(urls.TEAMS_CREATE, team_specification)
        return self.list_teams()

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

    def delete_file(self, source, dryrun):
        bucket = self.get_s3_information()
        if not dryrun:
            self.s3.Bucket(bucket['bucket']).delete_objects(Delete={'Objects': [{'Key': os.path.join(bucket['prefix'], *source.split("/"))}]})

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

    def download_fileobj(self, source, destination_obj, status_callback=None, dryrun=False):
        bucket = self.get_s3_information()
        if status_callback is not None:
            status_callback(
                'Downloading %s to object %s' % (os.path.join(*source.split("/")), "(dryrun)" if dryrun else ""))
        if not dryrun:
            self.s3.Bucket(bucket['bucket']).download_fileobj(os.path.join(bucket['prefix'], *source.split("/")), destination_obj)

    def upload_directory(self, source_dir, destination_prefix, rel_to='.', status_callback=None, dryrun=False):
        bucket = self.get_s3_information()
        source_dir_count = len(source_dir.split(os.path.sep)) - 1
        for root, dirs, files in os.walk(source_dir):
            for filename in files:
                local_path = os.path.join(root, filename)
                trailing_dir = root.split(os.path.sep)[source_dir_count:]
                relative_path = os.path.join(os.path.join(os.path.sep, *trailing_dir), filename)
                key = os.path.join(
                    bucket['prefix'], destination_prefix.strip("/"), *relative_path.split("/"))
                try:
                    self.s3.Object(bucket['bucket'], key).load()
                    if status_callback is not None:
                        status_callback('File found in data store, skipping %s %s' % (
                            key, "(dryrun)" if dryrun else ""))
                except ClientError as e:
                    if status_callback is not None:
                        status_callback(
                            "Uploading %s %s" % (os.path.join(bucket['prefix'], destination_prefix, relative_path),
                                                 "(dryrun)" if dryrun else ""))
                    if not dryrun:
                        self.s3.Bucket(bucket['bucket']).upload_file(
                            local_path, key)

    def download_directory(self, source, destination, status_callback=None, dryrun=False):
        bucket = self.get_s3_information()
        for obj in self.s3.Bucket(bucket['bucket']).objects.filter(Prefix=bucket['prefix'] + source):
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
                    self.s3.Bucket(bucket['bucket']).download_file(
                        obj.key, filename)
                except ClientError as e:
                    raise e

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

    def copy_file(self, source, destination, dryrun=False):
        """ Copy an object from one S3 location to another."""
        bucket = self.get_s3_information()
        if not dryrun:
            try:
                self.s3.Bucket(bucket['bucket']).copy({'Bucket': bucket['bucket'],
                                                       'Key': os.path.join(bucket['prefix'], *source.split("/"))},
                                                      os.path.join(bucket['prefix'], *destination.split("/")))
            except ClientError as e:
                raise e

    def move_file(self, source, destination, dryrun=False):
        self.copy_file(source, destination, dryrun)
        self.delete_file(source, dryrun)

    def _s3_copy(self, source, destination, dryrun=False):
        # S3 to S3 sync
        source_prefix = source[6:]
        destination_prefix = destination[6:]
        for file in self.list_epic_path(source_prefix):
            source_key = file['key']
            dest_key = s3_info['prefix'] + destination_prefix + file['key'].split('/',1)[1]
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
                    source_key = file['key']
                    destination_file = os.path.join(destination, file['key'].split('/',1)[1])
                    if os.path.isfile(destination_file):
                        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(destination_file), pytz.utc)
                        if mod_time >= file['last_modified']:
                            print("Skipping epic://{} as destination already exists".format(source_key))
                            continue
                    if dryrun:
                        print("Copying from epic://{} to {} (dryrun)".format(source_key, destination_file))
                    else:
                        print("Copying from epic://{} to {}".format(source_key, destination_file))
                        if not os.path.exists(os.path.dirname(destination_file)):
                            os.makedirs(os.path.dirname(destination_file))
                        self._download_file(s3_info['bucket'], source_key, str(destination_file))
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
                if file.startswith('./'):
                    dest_key = s3_info['prefix'] + destination_prefix + file[2:]
                else:
                    dest_key = s3_info['prefix'] + destination_prefix + file
                existing_file = self.get_key_info(dest_key)
                if existing_file:
                    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file), pytz.utc)
                    if existing_file['LastModified'] >= mod_time:
                        print("Skipping {} as destination already exists".format(file))
                        continue
                if dryrun:
                    print("Copying from {} to epic://{} (dryrun)".format(file, dest_key))
                else:
                    print("Copying from {} to epic://{}".format(file, dest_key))
                    self._upload_file(s3_info['bucket'], file, dest_key)
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

    def get_job_costs(self, job_definition={}):
        return self._post_request(urls.BATCH_JOB_COST, job_definition)

    def create_job(self, job_definition={}):
        return self._post_request(urls.BATCH_JOB_CREATE, job_definition)

    def cancel_job(self, job_id):
        self._post_request(urls.BATCH_JOB_CANCEL, {'pk': job_id})
        return self.get_job_details(job_id)

    def list_clusters(self, app_id, app_version_id):
        response = self._get_request(urls.CLUST_LIST + str(app_id) + '/' + str(app_version_id) + '/resources/')
        return response

    def delete_job(self, job_id):
        self._post_request(urls.BATCH_JOB_DELETE, {'job_id': job_id})
        return self.list_job_status()

    def list_applications(self):
        return self._get_request(urls.BATCH_APPLICATIONS)

    def list_application_versions(self, app_id):
        return self._get_request(urls.application_version(app_id))
