from setuptools import setup

setup(
    name="Epic_CLI",
    version=0.12,
    py_modules=['Epic_CLI'],
    install_requires=[
        'Click',
        'requests',
        'pyfiglet'
    ],
    entry_points='''
        [console_scripts]
        Epic_CLI=Epic_CLI:main
    '''
)
