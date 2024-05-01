# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO - DO NOT EDIT
import setuptools
import subprocess
try:
    import multiprocessing  # noqa
except ImportError:
    pass

def post_run(func):
    def wrapper():
        func()
        try:
            subprocess.run(["systemctl", "restart", "cc-hostrpc.service"], stderr=subprocess.DEVNULL, check=True)
            subprocess.run(["systemctl", "enable", "cc-hostrpc.service"], stderr=subprocess.DEVNULL, check=True)
        except subprocess.CalledProcessError:
            pass
    return wrapper


@post_run
def cc_setup():
    setuptools.setup(
        setup_requires=['pbr>=2.0.0'],
        pbr=True)


cc_setup()
