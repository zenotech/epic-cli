from setuptools import setup

setup(
    name="epiccli",
    version_command='git describe',
    py_modules=['epiccli','pyepic'],
    install_requires=[
        'Click',
        'requests',
        'pyfiglet',
        'boto3',
        'botocore'
    ],
    entry_points='''
        [console_scripts]
        epiccli=epiccli:main
    '''
)
