import click
import os
import requests
import pyfiglet
import boto3
from botocore import exceptions
from re import search

BASEURL = os.environ.get('EPIC_API_ENDPOINT', "https://epic.zenotech.com/api/v1")
DIR = os.path.expanduser('~/.epic')
TEAM = None


def get_request_headers():
    token = get_auth_token()
    if TEAM is not None:
        t = str(TEAM)
    else:
        t = None
    return {
        'Authorization': 'Token ' + token,
        'X-EPIC-TEAM': t
    }


@click.group()
@click.option('--team', type=int, help='ID of team to act as (optional)')
def main(team):
    global TEAM
    if team is not None:
        TEAM = team
    else:
        TEAM = None


@main.command()
@click.option('--username', prompt=True)
@click.option('--password', prompt=True, hide_input=True)
def auth(username, password):
    """Authenticate with EPIC. Stores auth key in ./bin file"""
    print(pyfiglet.Figlet().renderText("EPIC by Zenotech"))
    params = {'username': username, 'password': password}
    token = post_request(params, "/auth/", "")['token']
    if not os.path.exists(DIR):
        os.makedirs(DIR)
    with open(DIR + '/conf', 'w+') as f:
        f.write(token)


@main.group()
def accounts():
    """Services for EPIC Account Management"""
    print("Accounts:")


@main.group()
def billing():
    """ EPIC billing Management """
    pass


@billing.command("projectcodes")
def list_projectcodes():
    """Get ProjectCodes for current user or team"""
    response = get_request('/billing/projectcode/list/', get_request_headers())
    for i,val in enumerate(response):
        print(str(i) + ": " + str(val))


@accounts.command()
def aws_get():
    """Get AWS Credentials for current authenticated user"""
    response = get_request('/accounts/aws/get/', get_request_headers())
    for i in response:
        print(i + ": " + response[i])


@accounts.command()
def aws_create():
    """Create AWS Credentials, if the don't already exist"""
    get_request('/accounts/aws/create/', get_request_headers())


@accounts.command('list')
def team_list():
    """ List the User's teams"""
    response = get_request('/teams/list', get_request_headers())
    print("Teams: ")
    for k in response:
        print(str(k['team_id']) + ": " + k['name'])


@main.group()
def data():
    """Manage data in EPIC"""
    print("Data: ")


@data.command()
def aws_get():
    """Get the ARN for the User's S3 Bucket"""
    response = get_request('/data/aws/get/', get_request_headers())
    print("ARN: " + response)


@data.command()
@click.argument("filepath",required=False,type=str)
def ls(filepath):
    """List all data locations belonging to the user on EPIC"""
    if filepath is not None:
        params = {'dir':filepath}
    else:
        params = None
    response = get_request('/data/aws/list/', get_request_headers(),params)
    print("")
    print("Locations:")
    for i in response:
        print("- " + i)


@data.command()
@click.argument("filename")
@click.pass_context
def rm(ctx, filename):
    """Remove a file from EPIC"""
    client = create_boto_client()
    resp = client['client'].Bucket(client['bucket']).delete_objects(
        Delete={
            'Objects': [
                {
                    'Key': client['key'] + filename
                }
            ]
        }
    )
    if 'Deleted' in resp:
        print("Success Deleting")
        for i in resp['Deleted']:
            print("Deleted: " + str(i))
    if 'Errors' in resp:
        print("Error Deleting")
        for i in resp['Errors']:
            print("Error: " + str(i))
    ctx.invoke(ls)


@data.command()
@click.argument("source", type=click.Path())
@click.argument("destination", default='')
@click.pass_context
def cpu(ctx, source, destination):
    """Copy a file UP to EPIC"""
    client = create_boto_client()
    client['client'].Bucket(client['bucket']).upload_file(click.format_filename(source), client['key'] + destination)
    print(client['key'] + destination)
    ctx.invoke(ls)


@data.command()
@click.argument("source", default='')
@click.argument("destination", default='')
@click.pass_context
def cpd(source, destination):
    """Copy a file DOWN from EPIC"""
    client = create_boto_client()
    try:
        client['client'].Bucket(client['bucket']).download_file(client['key'] + source, destination)
    except exceptions.ClientError:
        print("Permission denied, is the filepath correct? (Requires a leading /)")


@data.command()
@click.argument("source")
@click.argument("destination")
@click.pass_context
def mv(ctx, source, destination):
    """Move a file within EPIC"""
    client = create_boto_client()
    copy_source = {
        'Bucket': client['bucket'],
        'Key': client['key'] + source
    }
    try:
        client['client'].Bucket(client['bucket']).copy(copy_source, client['key'] + destination)
        ctx.invoke(rm, filename=source)
    except exceptions.ClientError:
        print("Permission denied, is the filepath correct? (Requires a leading /)")


@main.group()
def job():
    """Services to do with EPIC Jobs and Clusters"""
    print("Jobs: ")


@job.command()
@click.option('--job_ID', default=1, prompt=True)
def status(job_id):
    """Get job status"""
    response = get_request(url='/batch/job/status/' + str(job_id), headers=get_request_headers())
    print("Status " + response['status'])


@job.command()
def submit():
    """Submit a new job to EPIC"""
    name = str(raw_input("Job Name: "))
    app_id = int(raw_input("App Version ID: "))
    queue_id = int(raw_input("Queue ID: "))
    working_dir_id = int(raw_input("Base Directory ID:"))
    params = {
        "name": name,
        "app_id": app_id,
        "queue_id": queue_id,
        "working_dir_id": working_dir_id
    }
    response = post_request(params, "/batch/job/create/", get_request_headers())
    print('Submitted, JobID: ' + str(response))


@job.command()
def list_jobs():
    """List active jobs"""
    response = get_request('/batch/job/list/', get_request_headers())
    print("")
    print("Active Jobs:")
    for i in response:
        print("- " + str(i['id']) + " | Finished? " + str(i['finished']))


@job.command()
@click.option('--app_id', default=1, prompt=True)
@click.option('--app_version_id', default=1, prompt=True)
def cluster_list(app_id, app_version_id):
    """List the clusters available for a given app"""
    response = get_request('/batch/app/' + str(app_id) + '/' + str(app_version_id) + '/resources/',
                           get_request_headers())
    print response
    for item in response:
        print("Queue Name: " + item['display_name'] + " | ID: " + str(item['id']))


@job.command()
@click.option('--jobId', default=1, prompt=True)
def delete(jobid):
    """Delete a running job"""
    post_request({'job_id': jobid}, '/batch/job/delete/', get_request_headers())


@main.group()
def app():
    """API Tools for applications on EPIC"""
    print("App:")


@app.command('list')
def list_app():
    """List apps available on EPIC and their IDs"""
    response = get_request('/batch/app/list', get_request_headers())
    print("")
    print("Apps")
    for item in response:
        print("- " + item['product']['name'] + "| ID: " + str(item['id']))


@app.command()
@click.option("--app_id", default=1, prompt=True)
def versions(app_id):
    """Given an app ID, list the available versions of it on EPIC"""
    response = get_request('/batch/app/' + str(app_id) + '/versions/', get_request_headers())
    for i in response:
        print("- " + i['version'] + ":" + str(i['id']))


def create_boto_client():
    creds = get_request('/accounts/aws/get/', get_request_headers())
    client = boto3.resource('s3',
                            aws_access_key_id=creds['aws_key_id'],
                            aws_secret_access_key=creds['aws_secret_key'])
    arn = get_request('/data/aws/get', get_request_headers())
    print(arn)
    try:
        bucket = search(r'[a-z-]+/', arn).group(0).rstrip('/')
        key = search(r'\d{2,}', arn.lstrip('arn:aws:s3:::')).group(0)
        print(bucket, key)
    except IndexError as e:
        print("Bucket Error: " + e.message)
        return
    return {'client': client, 'bucket': bucket, 'key': key}


def get_auth_token():
    try:
        token = open(DIR + '/conf', 'r').readline()
        return token
    except IOError:
        print("Auth token not found")
        exit(1)


def get_request(url, headers,params=None):
    r = requests.get(url=BASEURL + url, headers=headers,params=params)
    if r.status_code not in range(200, 299):
        print("Request Error: " + r.text)
        exit(1)
    else:
        print("Request Complete")
        try:
            return r.json()
        except ValueError:
            return "No Response"


def post_request(params, url, headers):
    r = requests.post(json=params, url=BASEURL + url, headers=headers)
    if r.status_code not in range(200, 299):
        print("Request Error: " + r.text)
        exit(1)
    else:
        print("Request Complete")
        try:
            return r.json()
        except ValueError:
            return "No Response"
