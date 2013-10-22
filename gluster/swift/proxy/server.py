# Copyright (c) 2012-2013 Red Hat, Inc.
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


# Simply importing this monkey patches the constraint handling to fit our
# needs
import mimetypes  # noqa
import gluster.swift.common.constraints  # noqa

from swift.proxy import server


class AccountController(server.AccountController):
    pass


class ContainerController(server.ContainerController):
    pass


class ObjectController(server.ObjectController):
    pass


class Application(server.Application):
    pass


def app_factory(global_conf, **local_conf):  # noqa
    """paste.deploy app factory for creating WSGI proxy apps."""
    conf = global_conf.copy()
    conf.update(local_conf)
    return Application(conf)
