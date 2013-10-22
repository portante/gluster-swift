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

""" Container Server for Gluster Swift UFO """

# Simply importing this monkey patches the constraint handling to fit our
# needs
import gluster.swift.common.constraints    # noqa

from swift.container import server
from gluster.swift.common.DiskDir import DiskDir


class ContainerController(server.ContainerController):
    """
    Subclass of the container server's ContainerController which replaces the
    _get_container_broker() method so that we can use Gluster's DiskDir
    duck-type of the container DatabaseBroker object, and make the
    account_update() method a no-op (information is simply stored on disk and
    already updated by virtue of performaing the file system operations
    directly).
    """

    def _get_container_broker(self, drive, part, account, container, **kwargs):
        """
        Overriden to provide the GlusterFS specific broker that talks to
        Gluster for the information related to servicing a given request
        instead of talking to a database.

        :param drive: drive that holds the container
        :param part: partition the container is in
        :param account: account name
        :param container: container name
        :returns: DiskDir object, a duck-type of DatabaseBroker
        """
        dev_path = self.devices.get_dev_path(drive)
        if not dev_path:
            return None
        return DiskDir(dev_path, account, container, self.logger, **kwargs)

    def account_update(self, req, account, container, broker):
        """
        Update the account server(s) with latest container info.

        For Gluster, this is just a no-op, since an account is just the
        directory holding all the container directories.

        :param req: swob.Request object
        :param account: account name
        :param container: container name
        :param broker: container DB broker object
        :returns: None.
        """
        return None


def app_factory(global_conf, **local_conf):
    """paste.deploy app factory for creating WSGI container server apps."""
    conf = global_conf.copy()
    conf.update(local_conf)
    return ContainerController(conf)
