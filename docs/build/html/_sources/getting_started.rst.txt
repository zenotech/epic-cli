Installation
************

Python 3.4+ is required. The package can be installed from PyPi using pip.

``pip install epiccli``


Authentication
**************

To use the API you will need an 'API token'. This can be retieved by logging into EPIC and viewing the API Token section on the Your Profile -> Your Credentials page.
Once you have a token you can configure the CLI by running:

``epic configure``

This will pronpt you for the url of EPIC, the default will suit most cases, and your API token. This configuration will then write this information to a config file stored in your user home.

Next time you use EPIC Cli it will load the token from that configration file. You can override this by using the ``--config`` option to load a different configuration file.

Alternatively you can supply your token directly by setting the EPIC_TOKEN environment variable.