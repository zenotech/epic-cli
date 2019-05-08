import click
import pyfiglet
import os
import errno
import pprint
import ConfigParser
from pyepic.core import (
    EpicClient,
    EpicConfigFile,
    check_path_is_folder
)
from pyepic.exceptions import ConfigurationException
from dateutil.parser import parse
from hurry.filesize import size
from hurry.filesize import alternative


def load_config(epic_url=None, epic_token=None, config_file=None):
    """
    Load config - priority args > env > file
    """
    EPIC_API_URL = "https://epic.zenotech.com"
    EPIC_TOKEN = None
    EPIC_TEAM = 0
    EPIC_PROJECT = 0
    if config_file is not None:
        click.echo("Loading config from %s" % config_file)
        ec = EpicConfigFile(config_file)
        EPIC_API_URL = ec.EPIC_API_URL
        EPIC_TOKEN = ec.EPIC_TOKEN
        EPIC_TEAM = ec.EPIC_TEAM
        EPIC_PROJECT = ec.EPIC_PROJECT
    EPIC_API_URL = os.environ.get('EPIC_API_ENDPOINT', EPIC_API_URL)
    EPIC_TOKEN = os.environ.get('EPIC_TOKEN', EPIC_TOKEN)
    EPIC_TEAM = int(os.environ.get('EPIC_TEAM', EPIC_TEAM))
    EPIC_PROJECT = int(os.environ.get('EPIC_PROJECT', EPIC_PROJECT))
    if epic_url is not None:
        EPIC_API_URL = epic_url
    if epic_token is not None:
        EPIC_TOKEN = epic_token

    return {
        'EPIC_API_URL': EPIC_API_URL,
        'EPIC_TOKEN': EPIC_TOKEN,
        'EPIC_TEAM': EPIC_TEAM,
        'EPIC_PROJECT': EPIC_PROJECT
    }


@click.group()
@click.pass_context
@click.option('--config', help='Configuration file to load (default is ~/.epic/config)')
def main(ctx, config):
    """CLI for communicating with the EPIC"""
    click.echo(pyfiglet.Figlet().renderText("EPIC by Zenotech"))
    config_file = os.path.expanduser('~/.epic/config')
    if not os.path.isfile(config_file):
        config_file = None

    if config is not None:
        if os.path.isfile(os.path.expanduser(config)):
            config_file = os.path.expanduser(config)
        else:
            raise click.ClickException("Config file %s not found" % config)
    try:
        config = load_config(None, None, config_file)
    except ConfigurationException:
        raise click.ClickException(
            "Configuration file not found or invalid, please run configure.")
    ec = EpicClient(config['EPIC_API_URL'],
                    config['EPIC_TOKEN'],
                    config['EPIC_TEAM'],
                    config['EPIC_PROJECT'])
    ctx.obj = ec


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
            raise click.ClickException(str(e))
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
    click.echo("ID | Name | Budget | Spend | Open")
    click.echo("-----------------------------")
    for project in ctx.obj.list_project_codes():
        open_str = "No" if project['closed'] else "Yes"
        budget = project['spend_limit'] if project['has_budget'] else "--"
        click.echo("{} | {} | {} | {} | {}".format(project['pk'],
                                                   project['project_id'],
                                                   budget,
                                                   project['current_spend'],
                                                   open_str))


@main.group()
@click.pass_context
def data(ctx):
    """Data Management"""
    pass


@data.command("ls")
@click.pass_context
@click.argument("filepath", required=False, type=str)
def list(ctx, filepath):
    """List data in your EPIC data store or in FILEPATH"""
    click.echo("EPIC data list")
    click.echo("Last Modified | Size | Path ")
    click.echo("-----------------------------")

    if filepath:
        filepath = filepath.strip('/')
    try:
        response = ctx.obj.list_data_locations(filepath)
        for folder in response['folders']:
            path = folder['obj_key'].split('/', 1)[1]
            last_modified = parse(folder['last_modified'])
            click.echo('{} | {} | {}'.format(last_modified.strftime("%m:%H %d-%m-%Y"), "--", '/' + path))
        for file in response['files']:
            path = file['obj_key'].split('/', 1)[1]
            last_modified = parse(file['last_modified'])
            click.echo('{} | {} | {}'.format(last_modified.strftime("%m:%H %d-%m-%Y"), size(file['size'], system=alternative), '/' + path))
    except Exception as e:
        raise click.ClickException("Error: {}".format(str(e)))


@data.command("rm")
@click.pass_context
@click.argument("filepath")
@click.option('--dryrun', help='Show what actions will take place but do not execute them', is_flag=True)
@click.option('--R', help='Recusive delete', is_flag=True)
def remove(ctx, filepath, dryrun, r):
    """Delete a file from EPIC"""
    if filepath.endswith("/"):
        click.echo("Deleting folder %s" % filepath)
        ctx.obj.delete_folder(filepath, dryrun)
    else:
        click.echo("Deleting file %s" % filepath)
        ctx.obj.delete_file(filepath, dryrun)


@data.command()
@click.pass_context
@click.argument("source",)
@click.argument("destination")
@click.option('--dryrun', help='Show what actions will take place but do not execute them', is_flag=True)
@click.option('-f', help='Overwrite file if it exists locally', is_flag=True)
def download(ctx, source, destination, dryrun, f):
    """Download a file from EPIC SOURCE to local DESTINATION
       SOURCE should be prefixed with "epic://"\n
       Example, download EPIC file from /my_sim_data/my.file to directory ./work/\n
       "epiccli sync download  epic://my_sim_data/my.file ./work/"\n
       To download whole folders use 'sync'.
    """
    try:
        if os.path.exists(destination):
            if os.path.isfile(destination):
                if not f:
                    click.echo("Destination file exists. Use -f to overwrite")
                    return
            elif os.path.isfile(destination + source.split('/')[-1]):
                if not f:
                    click.echo("Destination file exists. Use -f to overwrite")
                    return
        if not source.endswith("/"):
            ctx.obj.download_file(source, destination, dryrun=dryrun)
            click.echo("Download complete")
        else:
            click.echo("Please use 'sync' to download folders")
    except Exception as e:
        raise click.ClickException("Download failed, %s" % e)


def echo_callback(msg):
    click.echo(msg)


@data.command()
@click.pass_context
@click.argument("source",)
@click.argument("destination")
@click.option('--dryrun', help='Show what actions will take place but do not execute them', is_flag=True)
def upload(ctx, source, destination, dryrun):
    """Upload a file from local SOURCE to DESTINATION Folder
       Destinations should be prefixed with "epic://"\n
       Example, copy ~/my.file to EPIC folder /my_sim_data/\n
       "epiccli data upload ~/my.file epic://my_sim_data/"\n
       To upload a whole folder use 'sync'.
       """
    try:
        if os.path.exists(source):
            if os.path.isfile(source):
                source = click.format_filename(source)
                ctx.obj.upload_file(source, destination, dryrun=dryrun)
            else:
                click.echo("Please use 'sync' to upload folders")
        else:
            click.echo("File {} not found.".format(source))
    except Exception as e:
        raise click.ClickException("Upload failed, %s" % e)


@data.command()
@click.pass_context
@click.argument("source")
@click.argument("destination")
@click.option('--dryrun', help='Show what actions will take place but do not execute them', is_flag=True)
def sync(ctx, source, destination, dryrun):
    """Synchronise contents of SOURCE to DESTINATION.
       EPIC destinations should be prefixed with "epic://".
       Copies files from SOURCE that do not exist in DESTINATION.\n
       Example, copy from EPIC folder to local folder:\n
       "epiccli sync epic://my_sim_data/ ./local_folder/"  """
    try:
        if not check_path_is_folder(source):
            click.echo("Source does not appear to be a folder, please specify a folder for the source")
            return
        if not check_path_is_folder(destination):
            click.echo("Destination does appear to be a folder, please specify a folder for the destination")
            return
        click.echo('Synchronising from {} to {}'.format(source, destination))
        ctx.obj.sync_folders(source, destination, dryrun)
        click.echo('Sync complete')
    except Exception as e:
        raise click.ClickException("Sync failed, %s" % e)


@main.group()
@click.pass_context
def job(ctx):
    """Manage your EPIC jobs"""
    pass


def get_app_id(ctx):
    apps = ctx.obj.list_applications()
    for i in range(0, len(apps)):
        print(str(i) + ": " + apps[i]['product']['name'])
    app_name = apps[click.prompt("Select an application number: ", type=int)]['product']['name']
    for app in apps:
        if app[u'product'][u'name'] == app_name:
            versions = ctx.obj.list_application_versions(app[u'id'])
            print("Please select an application version: ")
            for i in range(0, len(versions)):
                print(str(i) + ": " + versions[i][u'version'])
            version = click.prompt("Number: ", type=int)
            return versions[version][u'id']
    raise NameError


@job.command()
@click.pass_context
def list(ctx):
    """List active jobs"""
    click.echo("Your EPIC HPC Jobs")
    click.echo("Job ID | Name | Application | Submitted by | Submitted | Status ")
    click.echo("-----------------------------------------")
    jlist = sorted(ctx.obj.list_job_status(), key=lambda k: k['id'])
    for job in jlist:
        created = parse(job['created'])
        click.echo("{} | {} | {} | {} | {} | {}".format(job['id'],
                                                        job['name'],
                                                        job['application'],
                                                        job['user'],
                                                        created.strftime("%m:%H %d-%m-%Y"),
                                                        job['latest_status']['status_display']))


@job.command()
@click.pass_context
@click.argument('job_id')
def cancel(ctx, job_id):
    """Cancel a job"""
    pprint.pprint("Cancelling job ID {}".format(job_id))
    pprint.pprint(ctx.obj.cancel_job(job_id))


@job.command()
@click.pass_context
@click.argument('ID')
def details(ctx, id):
    """Get details of job ID"""
    pprint.pprint(ctx.obj.get_job_details(id))


@main.group()
@click.pass_context
def teams(ctx):
    """Team Management"""
    pass


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
@click.option('--id', help="Switch to team with id", required=False, type=int)
def switch(ctx, id):
    """Switch your active EPIC team """
    if id:
        new_team_id = id
        teams_list = ctx.obj.list_teams()
    else:
        click.echo("Your available EPIC Teams (* current team)")
        click.echo("ID | Name")
        click.echo("-----------------")
        click.echo("0{} | Back to your account".format("*" if ctx.obj.EPIC_TEAM == 0 else ""))
        teams_list = ctx.obj.list_teams()
        for team in teams_list:
            team_id = team['team_id']
            click.echo("{}{} | {}".format(team_id, "*" if team_id == ctx.obj.EPIC_TEAM else "", team['name']))
        new_team_id = click.prompt("Enter the ID of the team you would like to switch to", type=int, default=ctx.obj.EPIC_TEAM)
    if new_team_id == 0:
        ctx.obj.EPIC_TEAM = 0
        ctx.obj.write_config_file()
        click.echo("Team ID set to %s" % new_team_id)
        return
    if not any(team['team_id'] == int(new_team_id) for team in teams_list):
        click.echo("Sorry, team with ID %s does not exist" % new_team_id)
    else:
        ctx.obj.EPIC_TEAM = int(new_team_id)
        ctx.obj.write_config_file()
        click.echo("Team ID set to %s" % new_team_id)


@main.group()
@click.pass_context
def queues(ctx):
    """Queue Management"""
    pass


@queues.command()
@click.pass_context
def list(ctx):
    """List your available EPIC queues"""
    click.echo("Your available EPIC HPC queues")
    click.echo("ID | Cluster Name | Queue Name | CPU Type | GPU Type | Total CPU Cores ")
    click.echo("-----------------------------------------")
    qlist = sorted(ctx.obj.list_queue_status(), key=lambda k: k['id'])
    for queue in qlist:
        click.echo("{} | {} | {} | {} | {} | {}".format(queue['id'],
                                                        queue['cluster_name'],
                                                        queue['name'],
                                                        queue['cpu_generation'],
                                                        queue.get('accelerator', "--"),
                                                        queue['max_cores']))


@queues.command()
@click.pass_context
@click.argument('ID')
def details(ctx, id):
    """Print the details of queue ID"""
    click.echo("HPC Cluster {} details".format(id))
    click.echo("-----------------------------------------")
    queue_details = ctx.obj.get_queue_details(id)
    pprint.pprint(queue_details)


if __name__ == '__main__':
    main()
