# BSD 3 - Clause License

# Copyright(c) 2020, Zenotech
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and / or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#         SERVICES
#         LOSS OF USE, DATA, OR PROFITS
#         OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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
        return not os.path.isfile(path)
