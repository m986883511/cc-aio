import os
import logging
import traceback

from oslo_config import cfg

from cs_utils import execute, func, file

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class GlanceEndPoint(object):
    def get_glance_backend(self, ctxt):
        settings = {}
        try:
            glance_conf = file.ini_file_to_dict(CONF.glance_api_conf_path)
        except Exception as e:
            LOG.error("failed to read %s! err=%s, exc=%s" % (CONF.glance_api_conf_path, str(e), traceback.format_exc()))
            return settings

        default_backend = glance_conf.get("glance_store", {}).get("default_backend")
        if not default_backend:
            return settings

        default_backend_config = glance_conf.get(default_backend, {})
        settings = {"default_backend": default_backend}
        settings.update(default_backend_config)
        return settings
