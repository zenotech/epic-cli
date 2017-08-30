from setuptools import setup

setup(
    name="Epic_CLI",
    version_command='git describe',
    py_modules=['Epic_CLI'],
    install_requires=[
        'Click',
        'requests',
        'pyfiglet',
        'boto3'
    ],
    entry_points='''
        [console_scripts]
        Epic_CLI=Epic_CLI:main
    '''
)
