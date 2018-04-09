import click
import pyfiglet
import os
import errno
import pprint
import json
import ConfigParser
from pyepic.core import EpicClient
from pyepic.exceptions import ConfigurationException


@click.group()
@click.pass_context
@click.option('--team', type=int, help='ID of team to act as (optional)')
@click.option('--config', help='Configuration file to load (default is ~/.epic/config)')
def main(ctx, team, config):
    """CLI for communicating with the EPIC"""
    click.echo(pyfiglet.Figlet().renderText("EPIC by Zenotech"))
    config_file = os.path.expanduser('~/.epic/config')
    if config is not None:
        if os.path.isfile(os.path.expanduser(config)):
            config_file = os.path.expanduser(config)
        else:
            click.echo("Config file %s not found" % config)
            exit(1)
    try:
        click.echo("Loading config from %s" % config_file)
        ec = EpicClient(config_file=config_file)
        ctx.obj = ec
    except ConfigurationException:
        click.echo(
            "Configuration file not found or invalid, please run configure.")


@main.command()
@click.pass_context
def configure(ctx):
    """ Configure the CLI tool """
    click.echo("Configuring EPIC Cli")
    default_url = "https://epic.zenotech.com"
    default_token = ""
    config_file = click.prompt(
        'Where would you like to store the config file?', default="~/.epic/config")
    if os.path.isfile(config_file):
        try:
            ec = EpicClient(config_file=config_file)
            default_url = ec.EPIC_API_URL
            default_token = ec.EPIC_TOKEN
        except ConfigurationException as e:
            pass
    epic_url = click.prompt(
        'Please enter the EPIC Url to connect to', default=default_url)
    if click.confirm('Do you already have an EPIC API token?'):
        token = click.prompt(
            'Please enter your EPIC API token', default=default_token)
    else:
        username = click.prompt('EPIC Username (email)?')
        password = click.prompt('Password?', hide_input=True)
        ec = EpicClient(epic_url=epic_url, epic_token="")
        token = ec.get_security_token(username, password)
    config = ConfigParser.RawConfigParser()
    config.add_section('epic')
    config.set('epic', 'url', epic_url)
    config.set('epic', 'token', token)
    config.set('epic', 'default_team', 0)
    config.set('epic', 'default_project', 0)
    config_file = os.path.expanduser(config_file)
    try:
        os.makedirs(os.path.dirname(config_file))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    with open(config_file, 'wb') as configfile:
        config.write(configfile)
        click.echo("Config file written to %s" % config_file)


@main.group()
@click.pass_context
def billing(ctx):
    """  Billing Management """
    pass

@billing.command("list_projects")
@click.pass_context
def list_projectcodes(ctx):
    """List your available project codes"""
    click.echo("Your available EPIC Projects:")
    for project in ctx.obj.list_project_codes():
        pprint.pprint(project)

@main.group()
@click.pass_context
def accounts(ctx):
    """Account Management"""
    pass

@main.group()
@click.pass_context
def teams(ctx):
    """Team Management"""
    pass

@accounts.command()
@click.pass_context
def notifications(ctx):
    """Get user notifications"""
    notifications = ctx.obj.list_user_notifications()
    pprint.pprint("Notifications")
    for item in notifications:
        pprint.pprint(item)

@accounts.command()
@click.pass_context
def clear(ctx):
    """Clear user notifications"""
    ctx.obj.delete_user_notifications()

@accounts.command()
@click.pass_context
def aws_get(ctx):
    """Get the user's EPIC AWS credentials"""
    pprint.pprint(ctx.obj.get_aws_tokens())

@accounts.command()
@click.pass_context
def aws_create(ctx):
    """Create EPIC AWS Credentials if they don't already exist"""
    pprint.pprint(ctx.obj.create_aws_tokens())
       

@main.group()
@click.pass_context
def data(ctx):
    """Data Management"""
    pass

@data.command()
@click.pass_context
def get_arn(ctx):
    """Get the ARN for the user's S3 Bucket"""
    pprint.pprint(ctx.obj.get_s3_location())

@data.command()
@click.pass_context
@click.argument("filepath", required=False, type=str)
def list(ctx, filepath):
    """List all data locations belonging to the user on EPIC"""
    click.echo("EPIC data list")
    click.echo("-----------------")
    if filepath:
        filepath = filepath.strip('/')
    response = ctx.obj.list_data_locations(filepath)
    for folder in response['folders']:
        path = folder['obj_key'].split('/', 1)[1]
        click.echo('/' + path)
    for file in response['files']:
        path = file['obj_key'].split('/', 1)[1]
        click.echo('/' + path)

@data.command()
@click.pass_context
@click.argument("filepath")
@click.option('--dryrun',is_flag=True)
def remove(ctx, filepath, dryrun):
    """Delete a file from EPIC"""
    pprint.pprint("Deleting file %s"%filepath)
    ctx.obj.delete_file(filepath, dryrun)
    pprint.pprint("Removed")

@data.command()
@click.pass_context
@click.argument("source",)
@click.argument("destination")
@click.option('--dryrun', is_flag=True)
def download(ctx, source, destination, dryrun):
    """Download a file from EPIC"""
    try:
        if source.endswith("/"):
            click.echo("Downloading %s to %s" % (source, destination))
            ctx.obj.download_directory(
                source, destination, status_callback=echo_callback, dryrun=dryrun)
            click.echo("Download complete")
        else:
            click.echo("Downloading %s to %s" % (source, destination))
            ctx.obj.download_file(source, destination, dryrun=dryrun)
            click.echo("Download complete")
    except Exception as e:
        click.echo("Download failed, %s" % e)


def echo_callback(msg):
    click.echo(msg)


@data.command()
@click.pass_context
@click.argument("source",)
@click.argument("destination")
@click.option('--dryrun', is_flag=True)
def upload(ctx, source, destination, dryrun):
    """Upload a file to EPIC"""
    try:
        if os.path.isfile(source):
            source = click.format_filename(source)
            click.echo("Uploading %s to %s" % (source, destination))
            ctx.obj.upload_file(source, destination, dryrun=dryrun)
            click.echo("Upload complete")
        else:
            click.echo("Uploading directory %s to %s" % (source, destination))
            ctx.obj.upload_directory(
                source, destination, status_callback=echo_callback, dryrun=dryrun)
            click.echo("Upload directory complete")
    except Exception as e:
        print("Upload failed, %s" % e)

@data.command()
@click.pass_context
@click.argument("source")
@click.argument("destination")
@click.option('--dryrun', is_flag=True)
def move(ctx,source,destination,dryrun):
    """Move a file from one location to another in EPIC"""
    try:
        click.echo('Moving %s to %s'%(source,destination))
        ctx.obj.move_file(source,destination,dryrun)
        click.echo('Move complete')
    except Exception as e:
        print("Move failed, %s" % e)


@main.group()
@click.pass_context
def job(ctx):
    """Submit or manage your EPIC jobs"""
    pass

@job.command()
@click.pass_context
def list_queues(ctx):
    """List current status of available queues"""
    pprint.pprint(ctx.obj.list_queue_status())

def get_app_id(ctx):
    apps = ctx.obj.list_applications()
    for i in range(0,len(apps)):
        print(str(i) + ": " + apps[i]['product']['name'])
    app_name = apps[click.prompt("Select an application number: ", type = int)]['product']['name']
    for app in apps:
        if app[u'product'][u'name'] == app_name:
            versions = ctx.obj.list_application_versions(app[u'id'])
            print("Please select an application version: ")
            for i in range(0,len(versions)):
                print(str(i) + ": " + versions[i][u'version'])
            version = click.prompt("Number: " , type=int)
            return versions[version][u'id']
    raise NameError 

@job.command()
@click.pass_context
@click.argument('appoptions',type=click.File('rb'), required=False)
def submit(ctx,appoptions):
    """Submit a new job to EPIC. AppOptions should be a plain text JSON formatted file that defines the specific
    options required for the application chosen."""
    name = str(raw_input("Job Name: "))
    try:
        app_id = get_app_id(ctx)
    except NameError:
        print("Application name/version not found in EPIC. Please use job/list_apps and job/versions to find valid versions.")
        return
    queue_id = int(raw_input("Queue ID: "))
    working_dir = str(raw_input("Base Directory: "))
    if appoptions is not None:
        try:
            app_options = json.loads(appoptions.read())
        except ValueError:
            print("AppOptions not a correctly formatted JSON file.")
            return
    else:
        app_options = {}
    job_definition = {
        "name": name,
        "app_id": app_id,
        "queue_id": queue_id,
        "working_dir_key": working_dir,
        "appoptions": app_options
    }
    response = ctx.obj.create_job(job_definition)
    click.echo('Submitted, JobID: ' + str(response))

@job.command()
@click.pass_context
def list_jobs(ctx):
    """List active jobs"""
    pprint.pprint(ctx.obj.list_job_status)

@job.command()
@click.argument('app_id')
@click.argument('app_version_id')
@click.pass_context
def cluster_list(ctx,app_id, app_version_id):
    """List the clusters available for a given app"""
    pprint.pprint(ctx.obj.list_clusters(app_id, app_version_id))

@job.command()
@click.pass_context
@click.argument('job_id')
def cancel(ctx, job_id):
    """Cancel a job"""
    pprint.pprint("Job cancelled.")
    pprint.pprint(ctx.obj.cancel_job(job_id))

@job.command()
@click.pass_context
@click.argument('job_id')
def delete(ctx, job_id):
    """Delete a job"""
    pprint.pprint("Job deleted.")
    pprint.pprint(ctx.obj.delete_job(job_id))

@job.command()
@click.pass_context
@click.option('--job', default=None)
def status(ctx, job):
    """Get job status"""
    if job:
        pprint.pprint(ctx.obj.get_job_status(job))
    else:
        pprint.pprint(ctx.obj.list_job_status())


@job.command()
@click.pass_context
def list_apps(ctx):
    """List apps available on EPIC and their IDs"""
    pprint.pprint(ctx.obj.list_applications())


@job.command()
@click.pass_context
@click.option("--app_id", default=1, prompt=True)
def version(ctx, app_id):
    """List apps available on EPIC and their IDs"""
    pprint.pprint(ctx.obj.list_application_versions(app_id))


@job.command()
@click.pass_context
@click.option("--appid", prompt=True)
@click.option("--tasklist", prompt=True)
def costs(ctx, appid, tasklist):
    """List apps available on EPIC and their IDs"""
    job_definition = {
        "application_id": appid,
        "tasks": tasklist
    }
    pprint.pprint(ctx.obj.get_job_costs(job_definition))

@teams.command()
@click.pass_context
def list(ctx):
    """List your available EPIC teams"""
    click.echo("Your available EPIC Teams (* current team)")
    click.echo("ID | Name")
    click.echo("-----------------")
    for team in ctx.obj.list_teams():
        if team['team_id'] == ctx.obj.EPIC_TEAM:
            click.echo(str(team['team_id']) + "* | " + team['name'])
        else:
            click.echo(str(team['team_id']) + " | " + team['name'])

@teams.command()
@click.pass_context
@click.argument('id', "ID to switch to", nargs=-1, required=False, type=int)
def switch(ctx, id):
    """Switch your active EPIC team"""
    if id:
        new_team_id = id[0]
        teams_list = ctx.obj.list_teams()
    else:
        click.echo("Your available EPIC Teams (* current team)")
        click.echo("ID | Name")
        click.echo("-----------------")
        teams_list = ctx.obj.list_teams()
        for team in teams_list:
            if team['team_id'] == ctx.obj.EPIC_TEAM:
                click.echo(str(team['team_id']) + "* | " + team['name'])
            else:
                click.echo(str(team['team_id']) + " | " + team['name'])
        new_team_id = click.prompt("Enter the ID of the team you would like to switch to", type=int, default=ctx.obj.EPIC_TEAM)
    if not any(team['team_id'] == int(new_team_id) for team in teams_list):
        click.echo("Sorry, team with ID %s does not exist" % new_team_id)
    else:
        ctx.obj.EPIC_TEAM = int(new_team_id)
        ctx.obj.write_config_file()
        click.echo("Team ID set to %s" % new_team_id)

if __name__ == '__main__':
    main()
