# Epic by Zenotech - Command Line Inteface

[EPIC](epic.zenotech.com) is a cloud platform for interfacing with HPC resources. This Python CLI demonstrates the REST API exposed on the EPIC platform and allows basic usage of the platform through the command line.

The CLI is built using [Click](http://click.pocoo.org/6/) to handle boilerplate and is packaged over pypi. To install for development purposes: clone the repo, create a venv and install the requirements.txt into it. Alternatively for normal usage run `pip install --editable .` with SU privallages to compile and install the entire package. Then run `Epic_CLI --help` for further guidance on how to continue.

The first step is to authenticate with EPIC. Running `Epic_CLI auth` will prompt for login details and store the recieved authentication token in an EPIC configuration file, by default at `~/.epic/conf`. This allows you to stay authenticated for the rest of your sessions, if you would like to authenticate as a different user, just run auth again.



For further documentation, a full API schema is available at https://epic.zenotech.com/api/v1/schema 
