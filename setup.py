from setuptools import setup

setup(
    name="epiccli",
    version_command='git describe',
    py_modules=['epiccli'],
    packages=['pyepic'],
    install_requires=[
        'Click',
        'requests',
        'pyfiglet',
        'boto3',
        'botocore',
        'pytz',
        'python-dateutil',
        'hurry.filesize'
    ],
    entry_points='''
        [console_scripts]
        epiccli=epiccli:main
    '''
)
