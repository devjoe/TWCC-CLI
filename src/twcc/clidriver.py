# -*- coding: utf-8 -*-
import time
import re
import requests
import json
import yaml
import datetime
import logging
import os
from twcc.session import session_start
from twcc.util import parsePtn, isNone
import urllib3
urllib3.disable_warnings()

class ServiceOperation:
    global _TWCC_SESSION_
    def __init__(self, debug=True):
        self._session_ = session_start()
        self.load_credential()
        self.load_yaml()

        self.try_alive()

        self.http_verb_valid = set(['get', 'post', 'delete', 'patch', 'put'])
        self.res_type_valid = set(['txt', 'json'])

        # for site usage
        self.header_extra = {}

        self._debug = debug
        if self._debug:
            self._setDebug()

    def try_alive(self):
        return True
        #print (requests.get(self.host_url, verify=False).status_code)
        #if not requests.get(self.host_url, verify=False).status_code == 404:
        #    raise ConnectionError
        #else:
        #    return True

    def load_credential(self):
        self.api_keys = self._session_.credentials
        self.host_url = self._session_.host
        #@todo
        try:
            self.def_proj = self._session_.def_proj
            self.def_s3_access_key = self._session_.def_s3_access_key
            self.def_s3_secret_key = self._session_.def_s3_secret_key
        except:
            self.def_proj = ""

    def load_yaml(self):

        self._yaml_fn_ = self._session_.files['resources']
        twcc_conf = yaml.load(open(self._yaml_fn_, 'r').read())
        self.stage = os.environ['_STAGE_']

        # change to load ~/.twcc_data/credential
        #self.host_url = twcc_conf[self.stage]['host']
        #self.api_keys = twcc_conf[self.stage]['keys']

        _ava_funcs_ = twcc_conf['avalible_funcs']

        self.valid_funcs = [_ava_funcs_[x]['name']
                            for x in range(len(_ava_funcs_))]
        self.valid_http_verb = dict([(_ava_funcs_[x]['name'], _ava_funcs_[x][
                                    'http_verb']) for x in range(len(_ava_funcs_))])
        self.url_format = dict([(_ava_funcs_[x]['name'],
                                 _ava_funcs_[x]['url_type']) for x in range(len(_ava_funcs_))])
        self.url_ptn = dict([
            (x, parsePtn(self.url_format[x])) for x in self.url_format.keys()])

        self.twcc_conf = twcc_conf

    def isFunValid(self, func):
        return True if func in self.valid_funcs else False

    def _api_act(self, t_api, t_headers, t_data=None, mtype="get"):

        start_time = time.time()

        if mtype == 'get':
            r = requests.get(t_api, headers=t_headers, verify=False)
        elif mtype == 'post':
            r = requests.post(t_api, headers=t_headers,
                              data=json.dumps(t_data), verify=False)
        elif mtype == "delete":
            r = requests.delete(t_api, headers=t_headers, verify=False)
        elif mtype == "patch":
            r = requests.delete(t_api, headers=t_headers, verify=False)
        elif mtype == "put":
            r = requests.put(t_api, headers=t_headers,
                              data=json.dumps(t_data), verify=False)
        else:
            raise ValueError("http verb:'{0}' is not valid".format(mtype))

        if self._debug:
            self._i(t_api)
            self._i(t_headers)
            self._i("--- URL: %s, Status: %s, (%.3f sec) ---" %
                    (t_api, r.status_code, time.time() - start_time))
        return (r, (time.time() - start_time))

    def doAPI(
        self,
            site_sn=None, api_host="_DEF_",
            key_tag=None, api_key="_DEF_",
            ctype="application/json",
            func="_DEF_",
            url_dict=None, data_dict=None, url_ext_get=None,
            http='get', res_type='json'):

        if not res_type in self.res_type_valid:
            raise ValueError(
                "Response type Error:'{0}' is not valid, available options: {1}".format(
                    res_type, ", ".join(self.res_type_valid)))

        if not self.isFunValid(func):
            raise ValueError("Function for:'{0}' is not valid".format(func))
        if not http in set(self.valid_http_verb[func]):
            raise ValueError("http verb:'{0}' is not valid".format(http))

        t_url = self.mkAPIUrl(site_sn, api_host, func, url_dict=url_dict)
        t_header = self.mkHeader(site_sn, key_tag, api_host, api_key, ctype)

        if not isNone(url_ext_get):
            t_url += "?"
            t_url_tmp = []
            for param_key in url_ext_get.keys():
                t_url_tmp.append( "{0}={1}".format(param_key, url_ext_get[param_key]) )
            t_url += "&".join(t_url_tmp)

        res = self._api_act(t_url, t_header, t_data=data_dict, mtype=http)
        if res_type in self.res_type_valid:
            if res_type == 'json':
                return res[0].json()
            elif res_type == 'txt':
                return res[0].content

    def mkHeader(self, site_sn=None, key_tag=None,
                 api_host="_DEF_", api_key="_DEF_",
                 ctype="application/json"):

        if not type(site_sn) == type(None):
            if re.match("\d+", site_sn):
                self.api_host = self.sites[site_sn]
            else:
                self.api_host = site_sn
        else:
            self.api_host = api_host
        if not type(key_tag) == type(None):
            self.api_key = self.api_keys[key_tag]
        else:
            self.api_key = api_key

        self.ctype = ctype

        return_header = {'X-API-HOST': self.api_host,
                'x-api-key': self.api_key,
                'Content-Type': self.ctype}

        if len(self.header_extra.keys())>0:
            for key in self.header_extra.keys():
                return_header[key] = self.header_extra[key]

        return return_header

    def _setDebug(self):
        log_dir = "{}/log".format(os.environ['TWCC_DATA_PATH'])
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_filename = datetime.datetime.now().strftime(
            log_dir + "/nchc_%Y%m%d_%H%M%S.log")
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(name)-8s %(levelname)-8s %(message)s',
            datefmt='%m-%d %H:%M:%S',
            filename=log_filename)
        # 定義 handler 輸出 sys.stderr
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)

        # 設定輸出格式
        formatter = logging.Formatter(
            '%(name)-12s: %(levelname)-8s %(message)s')
        # handler 設定輸出格式
        console.setFormatter(formatter)
        # 加入 hander 到 root logger
        logging.getLogger('').addHandler(console)

        # wrapper
        self._i = logging.info
        self._d = logging.debug
        self._w = logging.warning

    def show(self):
        self._i("-" * 10 + "=" * 10 + " [info] BEGIN " + "=" * 10 + "-" * 10)
        self._i(self.sites)
        self._i(self.keys)
        self._i("-" * 10 + "=" * 10 + " [info] ENDS  " + "=" * 10 + "-" * 10)

    def mkAPIUrl(self,
                 site_sn=None, api_host="_DEF_",
                 func="_DEF_", url_dict=None):

        # check if this function valid
        if not self.isFunValid(func):
            raise ValueError("API Function:'{0}' is not valid".format(func))

        url_ptn = self.url_ptn[func]
        url_str = self.url_format[func]
        url_parts = {}

        # check if this site_sn is valid
        if not type(site_sn) == type(None):
            self.api_pf = site_sn
        else:
            self.api_pf = api_host

        if "PLATFORM" in url_ptn.keys():
            url_parts['PLATFORM'] = self.api_pf

        # given url_dict
        ptn = func
        if not type(url_dict) == type(None):
            # check if function name is in given url_dict
            if func in url_dict:
                ptn = "%s/%s" % (func, url_dict[func])
                del url_dict[func]

                ptn += "/"+"/".join( ["%s/%s"%(k, url_dict[k]) for k in url_dict.keys()] )

                #todos
                ptn = ptn.strip("/")
            else:
                raise ValueError(
                    "Can not find '{0}' in provided dictionary.".format(func))

        if "FUNCTION" in url_ptn.keys():
            url_parts["FUNCTION"] = ptn

        t_url = url_str
        for ptn in url_parts.keys():
            t_url = t_url.replace(url_ptn[ptn], url_parts[ptn])

        return self.host_url + t_url
