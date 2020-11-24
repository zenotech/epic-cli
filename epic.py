import click
import pyfiglet
import os
import errno
import pprint
import json
import configparser
from epiccli.core import EpicClient
from epiccli.path import check_path_is_folder
from epiccli.exceptions import ConfigurationException
from dateutil.parser import parse
from hurry.filesize import size
from hurry.filesize import alternative
from pyepic.client import EPICClient

DEFAULT_URL = "https://epic.zenotech.com"


def format_localised_currency(data):
    return "{} {:.2f}".format(data.currency_symbol, data.amount)


@click.group()
@click.pass_context
@click.option("--config", help="Configuration file to load (default is ~/.epic/config)")
def main(ctx, config):
    """CLI for communicating with the EPIC"""
    click.echo(pyfiglet.Figlet().renderText("EPIC by Zenotech"))

    # Don't attempt to load an API client when we're configuring
    if ctx.invoked_subcommand == "configure":
        return

    config_file = os.path.expanduser("~/.epic/config")
    if config is not None:
        if os.path.isfile(os.path.expanduser(config)):
            config_file = os.path.expanduser(config)
        else:
            click.echo("Config file %s not found" % config)
            exit(1)
    try:
        click.echo("Loading config from %s" % config_file)
        # V1 API Client
        ec = EpicClient(config_file=config_file)

        # V2 API Client
        epic = EPICClient(
            connection_token=ec.EPIC_TOKEN,
            connection_url="{}/api/v2".format(ec.EPIC_API_URL),
        )

        ctx.obj = (ec, epic)
    except ConfigurationException:
        click.echo("Configuration file not found or invalid, please run configure.")
        exit(1)


@main.command()
@click.pass_context
def configure(ctx):
    """ Configure the CLI tool """
    click.echo("Configuring EPIC Cli")
    default_url = DEFAULT_URL
    default_token = ""
    config_file = "~/.epic/config"
    if os.path.isfile(config_file):
        try:
            ec = EpicClient(config_file=config_file)
            default_url = ec.EPIC_API_URL
            default_token = ec.EPIC_TOKEN
        except ConfigurationException as e:
            pass
    epic_url = click.prompt(
        "Please enter the EPIC Url to connect to", default=default_url
    )
    if click.confirm("Do you already have an EPIC API token?"):
        token = click.prompt("Please enter your EPIC API token", default=default_token)
    else:
        username = click.prompt("EPIC Username (email)?")
        password = click.prompt("Password?", hide_input=True)
        ec = EpicClient(epic_url=epic_url, epic_token="")
        token = ec.get_security_token(username, password)
    config = configparser.RawConfigParser()
    config.add_section("epic")
    config.set("epic", "url", epic_url)
    config.set("epic", "token", token)
    config.set("epic", "default_team", 0)
    config_file = os.path.expanduser(config_file)
    try:
        os.makedirs(os.path.dirname(config_file))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    with open(config_file, "w") as configfile:
        config.write(configfile)
        click.echo("Config file written to %s" % config_file)


@main.group()
@click.pass_context
def project(ctx):
    """  Project Management """
    pass


@project.command("list")
@click.pass_context
def list_projectcodes(ctx):
    """List your available project codes"""
    click.echo("Your available EPIC Projects:")
    click.echo("ID | Name | Budget | Spend | Open")
    click.echo("-----------------------------")
    for project in ctx.obj[1].list_projects():
        project_details = ctx.obj[1].get_project_details(project.pk)
        open_str = "No" if project_details.closed else "Yes"
        budget = (
            format_localised_currency(project_details.spend_limit)
            if project_details.has_budget
            else "--"
        )
        click.echo(
            "{} | {} | {} | {} | {}".format(
                project.pk,
                project.project_id,
                budget,
                format_localised_currency(project_details.current_spend),
                open_str,
            )
        )


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
        filepath = filepath.strip("/")
    try:
        response = ctx.obj[0].list_data_locations(filepath)
        for folder in response["folders"]:
            path = folder["obj_key"].split("/", 1)[1]
            last_modified = parse(folder["last_modified"])
            click.echo(
                "{} | {} | {}".format(
                    last_modified.strftime("%m:%H %d-%m-%Y"), "--", "/" + path
                )
            )
        for file in response["files"]:
            path = file["obj_key"].split("/", 1)[1]
            last_modified = parse(file["last_modified"])
            click.echo(
                "{} | {} | {}".format(
                    last_modified.strftime("%m:%H %d-%m-%Y"),
                    size(file["size"], system=alternative),
                    "/" + path,
                )
            )
    except Exception as e:
        click.echo("Error: {}".format(str(e)))


@data.command("rm")
@click.pass_context
@click.argument("filepath")
@click.option(
    "--dryrun",
    help="Show what actions will take place but do not execute them",
    is_flag=True,
)
@click.option("--R", help="Recusive delete", is_flag=True)
def remove(ctx, filepath, dryrun, r):
    """Delete a file from EPIC"""
    if filepath.endswith("/"):
        click.echo("Deleting folder %s" % filepath)
        ctx.obj[0].delete_folder(filepath, dryrun)
    else:
        click.echo("Deleting file %s" % filepath)
        ctx.obj[0].delete_file(filepath, dryrun)


@data.command()
@click.pass_context
@click.argument(
    "source",
)
@click.argument("destination")
@click.option(
    "--dryrun",
    help="Show what actions will take place but do not execute them",
    is_flag=True,
)
@click.option("-f", help="Overwrite file if it exists locally", is_flag=True)
def download(ctx, source, destination, dryrun, f):
    """Download a file from EPIC SOURCE to local DESTINATION
    SOURCE should be prefixed with "epic://"\n
    Example, download EPIC file from /my_sim_data/my.file to directory ./work/\n
    "epiccli sync download  epic://my_sim_data/my.file ./work/"\n
    to download whole folders use 'sync'.
    """
    try:
        if os.path.exists(destination):
            if os.path.isfile(destination):
                if not f:
                    click.echo("Destination file exists. Use -f to overwrite")
                    return
            elif os.path.isfile(destination + source.split("/")[-1]):
                if not f:
                    click.echo("Destination file exists. Use -f to overwrite")
                    return
        if not source.endswith("/"):
            ctx.obj[0].download_file(source, destination, dryrun=dryrun)
            click.echo("Download complete")
        else:
            click.echo("Please use 'sync' to download folders")
    except Exception as e:
        click.echo("Download failed, %s" % e)


def echo_callback(msg):
    click.echo(msg)


@data.command()
@click.pass_context
@click.argument(
    "source",
)
@click.argument("destination")
@click.option(
    "--dryrun",
    help="Show what actions will take place but do not execute them",
    is_flag=True,
)
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
                ctx.obj[0].upload_file(source, destination, dryrun=dryrun)
            else:
                click.echo("Please use 'sync' to upload folders")
        else:
            click.echo("File {} not found.".format(source))
    except Exception as e:
        print("Upload failed, %s" % e)


@data.command()
@click.pass_context
@click.argument("source")
@click.argument("destination")
@click.option(
    "--dryrun",
    help="Show what actions will take place but do not execute them",
    is_flag=True,
)
def sync(ctx, source, destination, dryrun):
    """Synchronise contents of SOURCE to DESTINATION.
    EPIC destinations should be prefixed with "epic://".
    Copies files from SOURCE that do not exist in DESTINATION.\n
    Example, copy from EPIC folder to local folder:\n
    "epiccli sync epic://my_sim_data/ ./local_folder/" """
    try:
        if not check_path_is_folder(source):
            click.echo(
                "Source does not appear to be a folder, please specify a folder for the source"
            )
            return
        if not check_path_is_folder(destination):
            click.echo(
                "Destination does appear to be a folder, please specify a folder for the destination"
            )
            return
        click.echo("Synchronising from {} to {}".format(source, destination))
        ctx.obj[0].sync_folders(source, destination, dryrun)
        click.echo("Sync complete")
    except Exception as e:
        print("Sync failed, %s" % e)


@main.group()
@click.pass_context
def job(ctx):
    """Manage your EPIC jobs"""
    pass


@job.command()
@click.pass_context
def list(ctx):
    """List active jobs"""
    click.echo("Your EPIC HPC Jobs")
    click.echo("Job ID | Name | Application | Submitted by | Submitted | Status ")
    click.echo("-----------------------------------------")
    jlist = ctx.obj[1].list_jobs()
    for job in jlist:
        click.echo(
            f"{job.id} | {job.name} | {job.app} | {job.submitted_by} | {job.submitted_at} | {job.status}"
        )


@job.command()
@click.pass_context
@click.argument("job_id")
def cancel(ctx, job_id):
    """Cancel a job"""
    click.echo("Cancelling job ID {}".format(job_id))
    pprint.pprint(ctx.obj[0].cancel_job(job_id))


@job.command()
@click.pass_context
@click.argument("ID")
def details(ctx, id):
    """Get details of job ID"""
    pprint.pprint(ctx.obj[1].get_job_details(id))


@main.group()
@click.pass_context
def team(ctx):
    """Team Management"""
    pass


@team.command()
@click.pass_context
def list(ctx):
    """List your available EPIC teams"""
    click.echo("Your available EPIC Teams (* current team)")
    click.echo("ID | Name")
    click.echo("-----------------")
    for team in ctx.obj[1].list_teams():
        if team.id == ctx.obj[0].EPIC_TEAM:
            click.echo(f"{team.id}* |  {team.name}")
        else:
            click.echo(f"{team.id} | {team.name}")


@team.command()
@click.pass_context
@click.option("--id", help="Switch to team with id", required=False, type=int)
def switch(ctx, id):
    """Switch your active EPIC team """
    if id:
        new_team_id = id
        teams_list = ctx.obj[1].list_teams()
    else:
        click.echo("Your available EPIC Teams (* current team)")
        click.echo("ID | Name")
        click.echo("-----------------")
        click.echo(
            "0{} | Back to your account".format(
                "*" if ctx.obj[0].EPIC_TEAM == 0 else ""
            )
        )
        teams_list = ctx.obj[1].list_teams()
        for team in teams_list:
            team_id = team.id
            click.echo(
                "{}{} | {}".format(
                    team_id,
                    "*" if team_id == ctx.obj[0].EPIC_TEAM else "",
                    team.name,
                )
            )
        new_team_id = click.prompt(
            "Enter the ID of the team you would like to switch to",
            type=int,
            default=ctx.obj[0].EPIC_TEAM,
        )
    if new_team_id == 0:
        ctx.obj[0].EPIC_TEAM = 0
        ctx.obj[0].write_config_file()
        click.echo("Team ID set to %s" % new_team_id)
        return
    if not any(team.id == int(new_team_id) for team in teams_list):
        click.echo("Sorry, team with ID %s does not exist" % new_team_id)
    else:
        ctx.obj[0].EPIC_TEAM = int(new_team_id)
        ctx.obj[0].write_config_file()
        click.echo("Team ID set to %s" % new_team_id)


@main.group()
@click.pass_context
def cluster(ctx):
    """Cluster Management"""
    pass


@cluster.command()
@click.pass_context
def list(ctx):
    """List your available EPIC clusters"""
    click.echo("Your available EPIC HPC queues")
    click.echo(
        "ID | Cluster Name | Queue Name | CPU Type | GPU Type | Total CPU Cores "
    )
    click.echo("-----------------------------------------")
    qlist = ctx.obj[1].list_clusters()
    for queue in qlist:
        click.echo(
            "{} | {} | {} | {} | {} | {}".format(
                queue.id,
                queue.name,
                queue.cluster_name,
                queue.resource_config.cpu_generation,
                queue.resource_config.accelerator.description
                if queue.resource_config.accelerator
                else "--",
                queue.max_allocation,
            )
        )


@cluster.command()
@click.pass_context
@click.argument("ID")
def details(ctx, id):
    """Print the details of queue ID"""
    click.echo(f"HPC Cluster {id} details")
    click.echo("-----------------------------------------")
    queue_details = ctx.obj[1].get_queue_details(id)
    pprint.pprint(queue_details)


if __name__ == "__main__":
    main()