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
import botocore

from pathlib import Path
from pyepic.client import EPICClient
from pyepic.applications.openfoam import OpenFoamJob
from pyepic.applications.zcfd import ZCFDJob
from pyepic.desktops import Desktop
from pyepic.desktops.desktop import MountType

from .core import EpicConfig
from .path import check_path_is_folder
from .exceptions import ConfigurationException, CommandError


DEFAULT_URL = "https://epic.zenotech.com"


def format_localised_currency(data):
    return "{} {:.2f}".format(data.currency_symbol, data.amount)


@click.group()
@click.pass_context
@click.option(
    "-c", "--config", help="Configuration file to load (default is ~/.epic/config)"
)
@click.option(
    "-p",
    "--profile",
    help="Load the named profile from the configuration file",
    default="default",
    show_default=True,
)
def main(ctx, config, profile):
    """CLI for communicating with the EPIC"""
    click.echo(pyfiglet.Figlet().renderText("EPIC by Zenotech"))

    # Don't attempt to load an API client when we're configuring
    if ctx.invoked_subcommand == "configure":
        return

    config_file = os.path.join(Path.home(), ".epic", "config")
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
        # Set the data source for file meta-data
        epic.data.meta_source = "CLI"

        # Store the config and SDK client in CLI context
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
    config_file = os.path.join(Path.home(), ".epic", "config")
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

    token = click.prompt("Please enter your EPIC API token", default=default_token)

    profile = click.prompt("Name of profile to store", default="default")

    config = configparser.ConfigParser()
    config_file = os.path.expanduser(config_file)
    if os.path.isfile(config_file):
        config.read(config_file)
    if not config.has_section(profile):
        config.add_section(profile)
    if epic_url.endswith("/"):
        epic_url = epic_url[:-1]
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


@data.command("info")
@click.pass_context
@click.argument("epicpath")
def info(ctx, epicpath):
    """List any file meta-data from EPIC"""
    if not epicpath.endswith("/"):
        try:
            meta = ctx.obj[1].data.get_file_meta_data(epicpath)
            click.echo(meta)
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] == "404":
                click.echo(f'File "{epicpath}" not found.')
    else:
        click.echo("Please specify a file rather than a folder")
    return


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
        click.echo(
            "Deleting folder {} {}".format(epicpath, "(dryrun)" if dryrun else "")
        )
        items = ctx.obj[1].data.delete(epicpath, dryrun=dryrun)
    else:
        click.echo("Deleting file {} {}".format(epicpath, "(dryrun)" if dryrun else ""))
        items = ctx.obj[1].data.delete(epicpath, dryrun=dryrun)
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


def sync_callback(source_path, target_path, uploaded, dryrun):
    if uploaded:
        click.echo(f"Copied {source_path} to {target_path} (dryrun={dryrun})")
    else:
        click.echo(f"Did not copy {source_path} to {target_path} (dryrun={dryrun})")


@data.command()
@click.pass_context
@click.argument("source")
@click.argument("destination")
@click.option(
    "--dryrun",
    help="Show what actions will take place but do not execute them",
    is_flag=True,
)
@click.option(
    "--overwrite/--no-overwrite",
    help="Overwrite existing files if last modified time is more recent in source",
    default=True,
    show_default=True,
)
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
                "Destination does not appear to be a folder, please specify a folder for the destination"
            )
            return
        click.echo(
            "Synchronising from {} to {} {}".format(
                source, destination, "(dryrun)" if dryrun else ""
            )
        )
        ctx.obj[1].data.sync(
            source,
            destination,
            dryrun=dryrun,
            callback=sync_callback,
            overwrite_existing=overwrite,
        )
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
@click.option("--n", default=10, help="List last n jobs", show_default=True)
def list(ctx, n):
    """List active jobs"""
    click.echo("Your EPIC HPC Jobs")
    click.echo("Job ID | Name | Application | Submitted by | Submitted | Status ")
    click.echo("----------------------------------------------------------------")
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


@job.command()
@click.pass_context
@click.argument("job_id")
def steps(ctx, job_id):
    """List the status of the job steps"""
    click.echo(f"Job Steps for Job ID {job_id}")
    click.echo("Step ID | Step Name | Status | Start | End | Wallclock | Exit Code")
    click.echo("------------------------------------------------------------------")
    details = ctx.obj[1].job.get_details(job_id)
    for step in details.job_steps:
        click.echo(
            f"{step.id} | {step.step_name} | {step.status} | {step.start} | {step.end} | {step.wallclock} | {step.exit_code}"
        )


@job.command()
@click.pass_context
@click.argument("step_id")
@click.option(
    "--log",
    type=click.Choice(["stdout", "stderr", "app"], case_sensitive=False),
    default="stdout",
    help="Which log file to tail",
    show_default=True,
)
def tail(ctx, step_id, log):
    """Get job log tail of step ID of job ID"""
    log_tail = ctx.obj[1].job.get_step_logs(step_id)
    click.echo(
        f'Tail of "{log}" log for Job Step {step_id} (last update {log_tail.last_update})'
    )
    click.echo(
        "-------------------------------------------------------------------------"
    )
    if log == "app":
        click.echo(log_tail.app)
    elif log == "stderr":
        click.echo(log_tail.stderr)
    elif log == "stdout":
        click.echo(log_tail.stdout)
    else:
        raise CommandError("Unknown log specified")


@job.group()
@click.pass_context
def create(ctx):
    """Create a job"""
    pass


@create.command()
@click.pass_context
@click.argument("job_name")
@click.argument("foam_version")
@click.argument("queue_code")
@click.argument("input_folder")
@click.option(
    "--np", default=1, help="Number of partitions for the solver", show_default=True
)
@click.option(
    "--cycles",
    default=0,
    help="Number of cycles to run the solver for, 0 to take value from controlDict",
    show_default=True,
)
@click.option(
    "--decompose/--no-decompose",
    " /-D",
    default=True,
    help="Run decomposePar",
    show_default=True,
)
@click.option(
    "--solve/--no-solve", " /-S", help="Run the solver", default=True, show_default=True
)
@click.option(
    "--reconstruct/--no-reconstruct",
    " /-R",
    help="Run reconstructPar",
    default=True,
    show_default=True,
)
@click.option(
    "--rs", default=1, help="Maximum solver runtime in hours", show_default=True
)
@click.option(
    "--rd", default=1, help="Maximum decomposePar runtime in hours", show_default=True
)
@click.option(
    "--rr", default=1, help="Maximum reconstructPar runtime in hours", show_default=True
)
def openfoam(
    ctx,
    job_name,
    foam_version,
    queue_code,
    input_folder,
    np,
    cycles,
    decompose,
    solve,
    reconstruct,
    rs,
    rd,
    rr,
):
    """Create a new OpenFoam job.

    Create a job called JOB_NAME using foam version FOAM_VERSION and run it on EPIC queue QUEUE_CODE.
    The data for the case should already have been uploaded to INPUT_FOLDER on EPIC.
    """
    click.echo(f"Creating OpenFoam job {job_name}")
    click.echo("----------------------------------")
    job = OpenFoamJob(foam_version, job_name, input_folder)

    job.decomposePar.execute = decompose
    job.decomposePar.runtime = rd

    job.solver.execute = solve
    job.solver.partitions = np
    job.solver.runtime = rs
    job.solver.endTime = cycles

    job.reconstructPar.execute = reconstruct
    job.reconstructPar.runtime = rr

    click.echo(f"Submitting to {queue_code}...")
    job_spec = job.get_job_create_spec(queue_code)

    # Submit the job
    job = ctx.obj[1].job.submit(job_spec)

    click.echo(f"Job {job_name} submitted. New job ID = {job[0].id}")


@create.command()
@click.pass_context
@click.argument("job_name")
@click.argument("zcfd_version")
@click.argument("queue_code")
@click.argument("input_folder")
@click.option(
    "--np", default=1, help="Number of partitions for the solver", show_default=True
)
@click.option(
    "--r", default=1, help="Maximum solver runtime in hours", show_default=True
)
@click.option(
    "--cycles",
    default=1000,
    help="Number of cycles to run the solver for",
    show_default=True,
)
@click.option("--p", help="Problem name, the name of the hdf5 file containing the mesh")
@click.option("--c", help="Case name, the name of the python control file")
@click.option("--restart/--no-restart", help="Is the run a restart?", default=False)
def zcfd(
    ctx, job_name, zcfd_version, queue_code, input_folder, np, r, cycles, p, c, restart
):
    """Create a new zCFD job.

    Create a job called JOB_NAME using foam version ZCFD_VERSION and run it on EPIC queue QUEUE_CODE.
    The data for the case should already have been uploaded to INPUT_FOLDER on EPIC.
    """
    click.echo(f"Creating zCFDFoam job {job_name}")
    click.echo("----------------------------------")

    job = ZCFDJob(
        zcfd_version,
        job_name,
        input_folder,
        c,
        p,
        cycles=cycles,
        restart=restart,
        partitions=np,
    )

    job.zcfd.runtime = r

    click.echo(f"Submitting to {queue_code}...")
    job_spec = job.get_job_create_spec(queue_code)

    # Submit the job
    job = ctx.obj[1].job.submit(job_spec)

    click.echo(f"Job {job_name} submitted. New job ID = {job[0].id}")


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
        "Queue Code | Cluster Name | Queue Name | CPU Type | GPU Type | Total CPU Cores "
    )
    click.echo("-----------------------------------------")
    qlist = ctx.obj[1].catalog.list_clusters()
    for queue in qlist:
        click.echo(
            "{} | {} | {} | {} | {} | {}".format(
                queue.queue_code,
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


@main.group()
@click.pass_context
def apps(ctx):
    """  Application Management """
    pass


@apps.command()
@click.pass_context
def list(ctx):
    """List your available EPIC applications"""
    click.echo("Your available EPIC application versions")
    click.echo("App Code | Product Name | Version | Available on cluster code")
    click.echo("-------------------------------------------------")
    alist = ctx.obj[1].catalog.list_applications()
    for app in alist:
        for version in app.versions:
            click.echo(
                "{} | {} | {} | {}".format(
                    version.app_code,
                    app.product.name,
                    version.version,
                    version.available_on,
                )
            )


@main.group()
@click.pass_context
def desktop(ctx):
    """  Desktop Management """
    pass


@desktop.command()
@click.pass_context
def list(ctx):
    """List your EPIC Desktop instances"""
    click.echo("Your available EPIC Teams")
    click.echo("ID | Status | Node Type | Launched by | Created")
    click.echo("-----------------")
    for desktop in ctx.obj[1].desktops.list():
        click.echo(
            f"{desktop.id} |  {desktop.status} | {desktop.node_type.node_code} | {desktop.launched_by} | {desktop.created.strftime('%Y-%m-%d %H:%M')}"
        )


@desktop.command()
@click.pass_context
def nodes(ctx):
    """List the available Desktop node types"""
    click.echo("Available EPIC Desktop node types")
    click.echo("Node Code | Name | Description")
    click.echo("-----------------------------")
    for desktop in ctx.obj[1].catalog.list_desktops():
        click.echo(f"{desktop.node_code} |  {desktop.name} | {desktop.description}")


@desktop.command()
@click.pass_context
@click.argument("desktop_id")
def details(ctx, desktop_id):
    """Get details of Desktop ID"""
    pprint.pprint(ctx.obj[1].desktops.get_details(desktop_id))


@desktop.command()
@click.pass_context
@click.argument("data_path")
@click.argument("node_type")
@click.argument("runtime", type=int)
@click.option(
    "--online",
    "mount_mode",
    flag_value="online",
    default=True,
    show_default=True,
    help="The DATA_PATH will be mounted directly on the Desktop and changes are automatically syncronised with EPIC",
)
@click.option(
    "--offline",
    "mount_mode",
    flag_value="offline",
    show_default=True,
    help="The data in DATA_PATH will be copied to the Desktop and changes not syncronised  with EPIC.",
)
@click.option(
    "--p", type=int, show_default=True, help="Launch destkop using project ID"
)
def launch(ctx, data_path, node_type, runtime, mount_mode, p):
    """Launch a new desktop using node with the node_code NODE_TYPE for RUNTIME hours. Mount data at epic path DATA_PATH on the Desktop."""
    click.echo("Launching new desktop...")
    desktop = Desktop(data_path, node_type)
    desktop.runtime = runtime
    desktop.mount_type = MountType(mount_mode)
    desktop.project_id = p
    pprint.pprint(ctx.obj[1].desktops.launch(desktop.get_launch_spec()))


@desktop.command()
@click.pass_context
@click.argument("desktop_id", type=int)
def terminate(ctx, desktop_id):
    """Terminate desktop ID"""
    click.echo("Terminating desktop ID {}".format(desktop_id))
    pprint.pprint(ctx.obj[1].desktops.terminate(desktop_id))


if __name__ == "__main__":
    main()
