Managing data 
*************
As well as job and desktop management EPIC CLI provides an easy way to get data to and from EPIC.

EPIC Paths
==========
EPIC CLI uses special url paths to identify data stored in EPIC. These use the prefix **"epic://"** and then the data location. For example if you had a folder in EPIC called "work" that contained a file called "input.file", then the EPIC path would be *"epic://work/input.file"*.

You can list all the available data in EPIC using the command::

        epic data ls


Uploading single files
======================

To upload a single file to epic you can use the command::

        epic data upload

Upload expects the first argument to be the local file and then the second argument to be the destination in EPIC. So for example to upload a local file called 'input.new' to a folder called work on EPIC you can do the following::

        epic data upload ./input.new epic://work/

If you supply a file name as the destination then the file will be uploaded with that name. For example to upload 'input.new' to 'work' as 'input_1.new' you can do::

        epic data upload ./input.new epic://work/input_1.new


Downloading single files
========================

Downloading a file from EPIC works the same way as uploading but the source should be an EPIC path and the destination a local file or folder.

For example, to download to a name file::

        epic data download epic://work/input.new ./input.new

Or, to download the file into a directory::

        epic data download epic://work/input.new ./folder/



Copying whole directories
=========================

Upload and download will let you copy single files but often you need to copy whole directories to and from EPIC. To do this you can use the command::

        epic data sync

'sync' will compare the source and destination folders and upload/download any new files or any files from the source that have newer timestamps than the destination. 

For example to copy everything from the remote work folder to a local directory called work you can run::

        epic data sync epic://work/ ./work/

Or to copy from the local directory back to EPIC you could run::
        
        epic data sync ./work/ epic://work/ 

Sync also has the option to add the **"--dryrun"** switch, this will cause the CLI to output the actions it would take without actually doing them. This is useful when you are copying large amounts of data and want to check the paths are as expected.
