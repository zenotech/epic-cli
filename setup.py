import os
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

version = os.environ.get("RELEASE_VERSION", "0.0.0")

setuptools.setup(
    name="epiccli",
    version=version,
    author="Zenotech Ltd",
    author_email="support@zenotech.com",
    description="A command line interface for EPIC HPC",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zenotech/epic-cli",
    py_modules=["epic"],
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    entry_points="""
        [console_scripts]
        epic=epic:main
    """,
    install_requires=[
        "Click",
        "requests",
        "pyfiglet",
        "boto3",
        "botocore",
        "pyepic>=0.0.6",
        "pytz",
        "python-dateutil",
        "hurry.filesize",
    ],
)
