import os
from re import search
import datetime


class EPICPath(object):
    def __init__(self, bucket: str, prefix: str, path: str, filename=None):
        self.protocol = "epic://"
        self.bucket = bucket
        self.prefix = prefix
        if path.startswith(self.protocol):
            self.path = path[len(self.protocol) :]
        else:
            self.path = path
        if self.path.endswith(os.sep):
            self.path = self.path[:-1]
        self.filename = filename

    def get_s3_key(self):
        if self.filename:
            return "/".join([self.prefix, self.path, self.filename])
        else:
            return "/".join([self.prefix, self.path])

    def get_user_string(self):
        if self.filename:
            return self.protocol + self.path + "/" + self.filename
        else:
            return self.protocol + self.path

    def get_local_path(self):
        if self.filename:
            return self.path.replace("/", os.sep) + os.sep + self.filename
        else:
            return self.path.replace("/", os.sep)


def local_to_epic_path(localfile: str):
    if localfile.startswith(os.sep):
        localfile = localfile[1:]

    if localfile.startswith(".{}".format(os.sep)):
        return localfile[2:].replace(os.sep, "/")
    else:
        return localfile.replace(os.sep, "/")


def check_path_is_folder(path: os.path):
    if path == ".":
        return True
    if path.startswith("epic://"):
        return path.endswith("/")
    else:
        return path.endswith(os.sep)
