# Epic by Zenotech - Command Line Interface
[![Documentation Status](https://readthedocs.org/projects/epic-cli/badge/?version=latest)](http://epic-cli.readthedocs.io/?badge=latest) [![PyPI version](https://badge.fury.io/py/epiccli.svg)](https://badge.fury.io/py/epiccli) 


[EPIC](epic.zenotech.com) is a cloud platform for interfacing with HPC resources. This Python CLI demonstrates the `pyepic` module, which interfaces with the EPIC REST API.

## Installation

### From PyPi
You can install the package from PyPi using pip with `pip install epiccli`

### Documentation
Documentation is available on [read the docs](http://epic-cli.readthedocs.io/?badge=latest).

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

The `pyepic` module manages interactions with the EPIC REST API. 

For further documentation, a full API schema is available at https://epic.zenotech.com/api/docs
