import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="epiccli",
    version_command='git describe',
    author="Zenotech Ltd",
    author_email="support@zenotech.com",
    description="A command line interface for EPIC HPC",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zenotech/epic-cli",
    py_modules=['epiccli'],
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    entry_points='''
        [console_scripts]
        epiccli=epiccli:main
    ''',
    install_requires=[
        'Click',
        'requests',
        'pyfiglet',
        'boto3',
        'botocore',
        'pytz',
        'python-dateutil',
        'hurry.filesize'
    ]
)
