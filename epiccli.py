import click
import pyfiglet
import os
import errno
import pprint
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


@billing.command("list_teams")
@click.pass_context
def list_teams(ctx):
    """List your available project teams"""
    click.echo("Your available EPIC Teams (* current team)")
    click.echo("ID | Name")
    click.echo("-----------------")
    for team in ctx.obj.list_teams():
        if (team['team_id'] == ctx.obj.EPIC_TEAM):
            click.echo(str(team['team_id']) + "* | " + team['name'])
        else:
            click.echo(str(team['team_id']) + " | " + team['name'])


@main.group()
@click.pass_context
def data(ctx):
    """Data Management"""
    pass


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


@job.command()
@click.pass_context
def submit(ctx):
    """Submit a new job to EPIC"""
    name = str(raw_input("Job Name: "))
    app_id = int(raw_input("App Version ID: "))
    queue_id = int(raw_input("Queue ID: "))
    working_dir = str(raw_input("Base Directory: "))
    job_definition = {
        "name": name,
        "app_id": app_id,
        "queue_id": queue_id,
        "working_dir_key": working_dir
    }
    response = ctx.obj.create_job(job_definition)
    click.echo('Submitted, JobID: ' + str(response))


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


if __name__ == '__main__':
    main()
