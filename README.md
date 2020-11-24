# Epic by Zenotech - Command Line Interface
[![Build
Status](https://travis-ci.org/zenotech/epic-cli.svg?branch=master)](https://travis-ci.org/zenotech/epic-cli) [![PyPI version](https://badge.fury.io/py/epiccli.svg)](https://badge.fury.io/py/epiccli) [![Updates](https://pyup.io/repos/github/zenotech/epic-cli/shield.svg)](https://pyup.io/repos/github/zenotech/epic-cli/)

[EPIC](epic.zenotech.com) is a cloud platform for interfacing with HPC resources. This Python CLI demonstrates the `pyepic` module, which interfaces with the EPIC REST API.

## Installation

### From PyPi
You can install the package from PyPi using pip with `pip install epiccli`

### From Github
Clone this repository and then install `epiccli` by navigating to the root directory and running `pip install --editable .`

## Usage
To get started run `epic configure` and enter your EPIC configuration details. This will generate the configuration file for the program.

Run `epic` to list commands:

    $ epic
    Usage: epic [OPTIONS] COMMAND [ARGS]...

      CLI for communicating with the EPIC

    Options:
      --help          Show this message and exit.

    Commands:
      cluster    Cluster Management
      configure  Configure the CLI tool
      data       Data Management
      job        Manage your EPIC jobs
      project    Project Management
      team       Team Management


## About
The CLI is built using [Click](http://click.pocoo.org/6/) to handle boilerplate and is packaged over pypi.

The `pyepic` module manages interactions with the EPIC REST API. It uses the [Requests](http://docs.python-requests.org/en/master/) and [boto3](https://boto3.readthedocs.io/en/latest/) modules to make expose methods to the user abstracting the more complicated HTTP requests that occur under the hood.

For further documentation, a full API schema is available at https://epic.zenotech.com/api/docs
