# BSD 3 - Clause License

# Copyright(c) 2020, Zenotech
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and / or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#         SERVICES
#         LOSS OF USE, DATA, OR PROFITS
#         OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import click
import pyfiglet
import os
import errno
import pprint
import json
import configparser
from pathlib import Path
from pyepic.client import EPICClient

from .core import EpicConfig
from .path import check_path_is_folder
from .exceptions import ConfigurationException


DEFAULT_URL = "https://epic.zenotech.com"


def format_localised_currency(data):
    return "{} {:.2f}".format(data.currency_symbol, data.amount)


@click.group()
@click.pass_context
@click.option('-c', "--config", help="Configuration file to load (default is ~/.epic/config)")
@click.option('-p', "--profile", help="Load the named profile from the configuration file", default="default", show_default=True)
def main(ctx, config, profile):
    """CLI for communicating with the EPIC"""
    click.echo(pyfiglet.Figlet().renderText("EPIC by Zenotech"))

    # Don't attempt to load an API client when we're configuring
    if ctx.invoked_subcommand == "configure":
        return

    config_file = os.path.join(Path.home(), '.epic', 'config')
    if config is not None:
        if os.path.isfile(os.path.expanduser(config)):
            config_file = os.path.expanduser(config)
        else:
            click.echo("Config file %s not found" % config)
            exit(1)
    try:
        click.echo("Loading config from %s" % config_file)
        
        config = EpicConfig(config_file=config_file, config_section=profile)

        # V2 API Client
        epic = EPICClient(
            connection_token=config.EPIC_TOKEN,
            connection_url="{}/api/v2".format(config.EPIC_API_URL),
        )

        ctx.obj = (config, epic)
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
    config_file = os.path.join(Path.home(), '.epic', 'config')
    if os.path.isfile(config_file):
        try:
            config = EpicConfig(config_file=config_file)
            default_url = config.EPIC_API_URL
            default_token = config.EPIC_TOKEN
        except ConfigurationException as e:
            pass
    
    epic_url = click.prompt(
        "Please enter the EPIC Url to connect to", default=default_url
    )

    token = click.prompt(
        "Please enter your EPIC API token", default=default_token
    )

    profile = click.prompt(
        "Name of profile to store", default='default'
    )

    config = configparser.ConfigParser()
    config_file = os.path.expanduser(config_file)
    if os.path.isfile(config_file):
        config.read(config_file)
    if not config.has_section(profile):
        config.add_section(profile)
    config.set(profile, "url", epic_url)
    config.set(profile, "token", token)
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
    for project in ctx.obj[1].projects.list():
        project_details = ctx.obj[1].projects.get_details(project.pk)
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
@click.argument("epicpath", required=False, type=str)
def list(ctx, epicpath):
    """List data in your EPIC data store"""
    click.echo("EPIC data list")
    click.echo("-----------------------------")

    if epicpath is None:
        epicpath = "epic://"
    try:
        response = ctx.obj[1].data.ls(epicpath)
        for item in response:
            click.echo(f"{item.obj_path}")
    except Exception as e:
        click.echo("Error: {}".format(str(e)))


@data.command("rm")
@click.pass_context
@click.argument("epicpath")
@click.option(
    "--dryrun",
    help="Show what actions will take place but do not execute them",
    is_flag=True,
)
def delete(ctx, epicpath, dryrun):
    """Delete a file from EPIC"""
    if epicpath.endswith("/"):
        click.echo("Deleting folder {} {}".format(epicpath, "(dryrun)" if dryrun else ""))
        items = ctx.obj[1].data.delete(epicpath, dryrun = dryrun)
    else:
        click.echo("Deleting file {} {}".format(epicpath, "(dryrun)" if dryrun else ""))
        items = ctx.obj[1].data.delete(epicpath, dryrun = dryrun)
    for item in items:
        click.echo("Deleted {} {}".format(item, "(dryrun)" if dryrun else ""))
    return

@data.command()
@click.pass_context
@click.argument(
    "source",
)
@click.argument("destination")
@click.option("-f", help="Overwrite file if it exists locally", is_flag=True)
def download(ctx, source, destination, f):
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
            ctx.obj[1].data.download_file(source, destination)
            click.echo("Download complete")
        else:
            click.echo("Please use 'sync' to download folders")
    except Exception as e:
        click.echo("Download failed, %s" % e)


@data.command()
@click.pass_context
@click.argument(
    "source",
)
@click.argument("destination")
def upload(ctx, source, destination):
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
                ctx.obj[1].data.upload_file(source, destination)
            else:
                click.echo("Please use 'sync' to upload folders")
        else:
            click.echo("File {} not found.".format(source))
    except Exception as e:
        print("Upload failed, %s" % e)


def sync_callback(source_path, target_path, uploaded):
    if uploaded:
        click.echo(f"Copied {source_path} to {target_path}")
    else:
        click.echo(f"Did not copy {source_path} to {target_path}")

@data.command()
@click.pass_context
@click.argument("source")
@click.argument("destination")
@click.option(
    "--dryrun",
    help="Show what actions will take place but do not execute them",
    is_flag=True,
)
@click.option('--overwrite/--no-overwrite',
              help="Overwrite existing files if last modified time is more recent in source",
              default=True,
              show_default=True)
def sync(ctx, source, destination, dryrun, overwrite):
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
        click.echo("Synchronising from {} to {} {}".format(source, destination, "(dryrun)" if dryrun else ""))
        ctx.obj[1].data.sync(source, destination, dryrun=dryrun, callback=sync_callback, overwrite_existing=overwrite)
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
@click.option('--n', default=10, help="List last n jobs",  show_default=True)
def list(ctx, n):
    """List active jobs"""
    click.echo("Your EPIC HPC Jobs")
    click.echo("Job ID | Name | Application | Submitted by | Submitted | Status ")
    click.echo("-----------------------------------------")
    jlist = ctx.obj[1].job.list(limit=n)
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
    pprint.pprint(ctx.obj[1].job.cancel(job_id))


@job.command()
@click.pass_context
@click.argument("job_id")
def details(ctx, job_id):
    """Get details of job ID"""
    pprint.pprint(ctx.obj[1].job.get_details(job_id))


@main.group()
@click.pass_context
def team(ctx):
    """Team Management"""
    pass


@team.command()
@click.pass_context
def list(ctx):
    """List your available EPIC teams"""
    click.echo("Your available EPIC Teams")
    click.echo("ID | Name")
    click.echo("-----------------")
    for team in ctx.obj[1].teams.list():
        click.echo(f"{team.id} |  {team.name}")


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
    qlist = ctx.obj[1].catalog.list_clusters()
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
    queue_details = ctx.obj[1].catalog.queue_details(id)
    pprint.pprint(queue_details)


if __name__ == "__main__":
    main()
