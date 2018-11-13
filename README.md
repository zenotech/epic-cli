# Epic by Zenotech - Command Line Interface
[![Build
Status](https://travis-ci.org/zenotech/epic-cli.svg?branch=master)](https://travis-ci.org/zenotech/epic-cli) [![Updates](https://pyup.io/repos/github/zenotech/epic-cli/shield.svg)](https://pyup.io/repos/github/zenotech/epic-cli/)

[EPIC](epic.zenotech.com) is a cloud platform for interfacing with HPC resources. This Python CLI demonstrates the `pyepic` module, which interfaces with the EPIC REST API.

Once this repo has been cloned, install `epiccli` by navigating to the root directory and running `pip install --editable .`

The CLI is built using [Click](http://click.pocoo.org/6/) to handle boilerplate and is packaged over pypi. Once installed, run `epiccli configure` to generate the configuration file for the program. Multiple configuration files can be stored and can be chosen between using the `--config` flag. By default the file at `~/.epic/config` is loaded. 

The file `Epic_CLI.py` contains a deprecated version of EpicCLI which consists of the functionalities of `pyepic` and `epiccli` combined. It is left for reference reasons.

The `pyepic` module manages interactions with the EPIC REST API. It uses the [Requests](http://docs.python-requests.org/en/master/) and [boto3](https://boto3.readthedocs.io/en/latest/) modules to make expose methods to the user abstracting the more complicated HTTP requests that occur under the hood.


For further documentation, a full API schema is available at https://epic.zenotech.com/api/v1/schema 
