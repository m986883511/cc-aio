import os
import logging
import traceback

from oslo_config import cfg

from cs_utils import execute, func, file

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class CinderEndPoint(object):
    def get_cinder_backends(self, ctxt):
        backends = []
        try:
            cinder_conf = file.ini_file_to_dict(CONF.cinder_volume_conf_path)
        except Exception as e:
            LOG.error('failed to read, err={}, exc={}'.format(str(e), traceback.format_exc()))
            return backends

        enabled_backends = cinder_conf.get('DEFAULT', {}).get('enabled_backends', "").split(",")
        have_backends = {k: v for k, v in cinder_conf.items() if "volume_driver" in v}
        backend_types = {
            "cinder.volume.drivers.rbd.RBDDriver": "rbd",
            "cinder.volume.drivers.nfs.NfsDriver": "nfs",
            "cinder.volume.drivers.lvm.LVMVolumeDriver": "lvm",
        }
        for name, value in have_backends.items():
            setting = {
                'id': name,
                'name': value.get("volume_backend_name"),
                'driver': value.get("volume_driver"),
                'type': backend_types.get(value.get("volume_driver")),
                'enabled': bool(value.get("volume_backend_name") in enabled_backends)
            }
            backends.append(setting)
        return backends
