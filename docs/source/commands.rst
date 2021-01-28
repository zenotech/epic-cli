Usage
*****
Running ``epic`` will list the available commands::

        >epic
        Usage: epic [OPTIONS] COMMAND [ARGS]...

        CLI for communicating with the EPIC

        Options:
        --config TEXT  Configuration file to load (default is ~/.epic/config)
        --help         Show this message and exit.

        Commands:
        cluster    Cluster Management
        configure  Configure the CLI tool
        data       Data Management
        job        Manage your EPIC jobs
        project    Project Management
        team       Team Management

You can get more detailed help by adding the ``--help`` option::

        >epic data download --help
        _____ ____ ___ ____   _             _____                _            _     
        | ____|  _ \_ _/ ___| | |__  _   _  |__  /___ _ __   ___ | |_ ___  ___| |__  
        |  _| | |_) | | |     | '_ \| | | |   / // _ \ '_ \ / _ \| __/ _ \/ __| '_ \ 
        | |___|  __/| | |___  | |_) | |_| |  / /|  __/ | | | (_) | ||  __/ (__| | | |
        |_____|_|  |___\____| |_.__/ \__, | /____\___|_| |_|\___/ \__\___|\___|_| |_|
                                    |___/                                           

        Loading config from /Users/user/.epic/config
        Usage: epic data download [OPTIONS] SOURCE DESTINATION

        Download a file from EPIC SOURCE to local DESTINATION SOURCE should be
        prefixed with "epic://"

        Example, download EPIC file from /my_sim_data/my.file to directory ./work/

        "epiccli sync download  epic://my_sim_data/my.file ./work/"

        to download whole folders use 'sync'.

        Options:
        -f      Overwrite file if it exists locally
        --help  Show this message and exit.


