import os
import logging
import traceback

from oslo_config import cfg

from cs_utils import execute, func, file

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class KeystoneEndPoint(object):
    def get_ldap_settings(self, ctxt):
        def get_err_settings(err_msg):
            LOG.error(err_msg)
            settings['error'] = err_msg
            return settings

        settings = {}
        try:
            keystone_conf = file.ini_file_to_dict(CONF.keystone_conf_path)
        except Exception as e:
            err_msg = "failed to read keystone.conf! err={}, exc={}".format(str(e), traceback.format_exc())
            return get_err_settings(err_msg)
        
        domain_specific_drivers_enabled = keystone_conf.get('identity', {}).get('domain_specific_drivers_enabled')
        # domain_config_dir = keystone_conf.get('identity', {}).get('domain_config_dir')
        if not domain_specific_drivers_enabled or domain_specific_drivers_enabled.lower() != 'true':
            err_msg = f"not open ldap identity, domain_specific_drivers_enabled={domain_specific_drivers_enabled}"
            return get_err_settings(err_msg)

        ldap_conf_path = os.path.join(CONF.keystone_domain_conf_path, 'keystone.ldap.conf')
        if not os.path.exists(ldap_conf_path):
            err_msg = f"ldap conf path is not exist, path={ldap_conf_path}"
            return get_err_settings(err_msg)
        
        try:
            ldap_conf = file.ini_file_to_dict(ldap_conf_path)
        except Exception as e:
            err_msg = f"failed to read {ldap_conf_path}! err={str(e)}, exc={traceback.format_exc()}"
            return get_err_settings(err_msg)

        user = func.get_dict_dict_value(ldap_conf, 'ldap', 'user') or ''
        domain_name = ""
        for u in user.split(','):
            if u.split('=')[0] == 'dc':
                if domain_name == '':
                    domain_name = u.split('=')[1]
                else:
                    domain_name += "." + u.split('=')[1]
        settings["domain_name"] = domain_name

        try:
            settings["user"] = user.split(',')[0].split('=')[1]
        except Exception as e:
            err_msg = "failed to get ldap user! err=%s, exc=%s" % (str(e), traceback.format_exc())
            return get_err_settings(err_msg)

        ldap_url = func.get_dict_dict_value(ldap_conf, 'ldap', 'url')
        if '//' not in ldap_url:
            err_msg = f"ldap url config is not correct, not have '//', url={ldap_url}"
            return get_err_settings(err_msg)

        temp = {
            'server_addr': ldap_url.split('//')[1],
            'searchbase': func.get_dict_dict_value(ldap_conf, 'ldap', 'user_tree_dn') or '',
            'password': func.get_dict_dict_value(ldap_conf, 'ldap', 'password') or '',
        }
        settings.update(temp)
        return settings
