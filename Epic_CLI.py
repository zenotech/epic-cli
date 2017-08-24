import click
import os
import requests
import pyfiglet

BASEURL = "https://epic-qa.zenotech.com/api/v1"
DIR = os.path.expanduser('~/.epic')


@click.group()
def main():
    print(pyfiglet.Figlet().renderText("EPIC by Zenotech"))


@main.command()
@click.option('--username', prompt=True)
@click.option('--password', prompt=True, hide_input=True)
def auth(username, password):
    """Authenticate with EPIC. Stores auth key in ./bin file"""
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


@accounts.command()
def aws_get():
    """Get AWS Credentials for current authenticated user"""
    token = get_auth_token()
    response = get_request('/accounts/aws/get/', {'Authorization': 'Token ' + token})
    for i in response:
        print(i + ": " + response[i])


@accounts.command()
def aws_create():
    """Create AWS Credentials, if the don't already exist"""
    token = get_auth_token()
    get_request('/accounts/aws/create/', {'Authorization': 'Token ' + token})


@accounts.command()
def team_get():
    """Get the User's current team"""
    token = get_auth_token()
    response = get_request('/accounts/team/get/', {'Authorization': 'Token ' + token})
    print("Current Team: " + str(response))


@accounts.command()
@click.option("--teamPk", prompt=True, default=1)
@click.pass_context
def team_set(ctx, teampk):
    """Set your active team role"""
    token = get_auth_token()
    params = {'teamPk': teampk}
    post_request(params=params, url='/accounts/team/set/', headers={'Authorization': 'Token ' + token})
    ctx.invoke(team_get)


@main.group()
def data():
    """Manage data in EPIC"""
    print("Data: ")


@data.command()
def aws_get():
    """Get the ARN for the User's S3 Bucket"""
    token = get_auth_token()
    response = get_request('/data/aws/get/', {'Authorization': 'Token ' + token})
    print("ARN: " + response)


@data.command()
def aws_list():
    """List all data locations belonging to the user on EPIC"""
    token = get_auth_token()
    response = get_request('/data/aws/list/', {'Authorization': 'Token ' + token})
    print("")
    print("Locations:")
    for i in response:
        print("- " + i)


@main.group()
def job():
    """Services to do with EPIC Jobs and Clusters"""
    print("Jobs: ")


@job.command()
@click.option('--job_ID', default=1, prompt=True)
def status(job_id):
    """Get job status"""
    token = get_auth_token()
    response = get_request(url='/batch/job/status/' + str(job_id), headers={'Authorization': 'Token ' + token})
    print("Status " + response['status'])


@job.command()
def submit():
    """Submit a new job to EPIC"""
    token = get_auth_token()
    name = str(raw_input("Job Name: "))
    app_id = int(raw_input("App ID: "))
    queue_id = int(raw_input("Queue ID: "))
    working_dir_id = int(raw_input("Base Directory ID:"))
    params = {
        "name": name,
        "app_id": app_id,
        "queue_id": queue_id,
        "working_dir_id": working_dir_id
    }
    response = post_request(params, "/batch/job/create/", {'Authorization': 'Token ' + token})
    print('Submitted, JobID: ' + str(response))


@job.command()
def list_jobs():
    """List active jobs"""
    token = get_auth_token()
    response = get_request('/batch/job/list/', {'Authorization': 'Token ' + token})
    print("")
    print("Active Jobs:")
    for i in response:
        print("- " + str(i['id']) + " | Finished? " + str(i['finished']))


@job.command()
@click.option('--app_id', default=1, prompt=True)
def cluster_list(app_id):
    token = get_auth_token()
    response = get_request('/batch/queue/get/' + str(app_id), {'Authorization': 'Token ' + token})
    for item in response:
        print("Queue Name: " + item['display_name'] + " | ID: " + str(item['id']))


@job.command()
@click.option('--jobId', default=1, prompt=True)
def delete(jobid):
    token = get_auth_token()
    post_request({'job_id': jobid}, '/batch/job/delete/', {'Authorization': 'Token ' + token})


@main.group()
def app():
    """API Tools for applications on EPIC"""
    print("App:")


@app.command()
def list_app():
    token = get_auth_token()
    response = get_request('/batch/app/list', {'Authorization': 'Token ' + token})
    print("")
    print("Apps")
    for item in response:
        print("- " + item['product']['name'] + "| ID: " + str(item['id']))


@app.command()
@click.option("--app_Id", default=1, prompt=True)
def versions(app_id):
    token = get_auth_token()
    response = get_request('/batch/app/' + str(app_id) + '/versions/', {'Authorization': 'Token ' + token})
    for i in response:
        print("- " + i['version'] + ":" + str(i['id']))


def get_auth_token():
    try:
        token = open(DIR + '/conf', 'r').readline()
        return token
    except IOError:
        print("Auth token not found")
        exit(1)


def get_request(url, headers):
    r = requests.get(url=BASEURL + url, headers=headers)
    if r.status_code not in range(200, 299):
        print("Request Error: " + r.text)
        exit(1)
    else:
        print("Request Complete")
        return r.json()


def post_request(params, url, headers):
    r = requests.post(json=params, url=BASEURL + url, headers=headers)
    if r.status_code not in range(200, 299):
        print("Request Error: " + r.text)
        exit(1)
    else:
        print("Request Complete")
        return r.json()
