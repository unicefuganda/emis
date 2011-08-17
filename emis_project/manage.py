#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

import sys, os
from django.core.management import execute_manager
import settings

filedir = os.path.dirname(__file__)
sys.path.append(os.path.join(filedir))
sys.path.append(os.path.join(filedir,'rapidsms','lib'))
sys.path.append(os.path.join(filedir,'rapidsms_auth'))
sys.path.append(os.path.join(filedir,'rapidsms_contact'))
sys.path.append(os.path.join(filedir,'rapidsms_cvs'))
sys.path.append(os.path.join(filedir,'rapidsms_generic'))
sys.path.append(os.path.join(filedir,'rapidsms_httprouter_src'))
sys.path.append(os.path.join(filedir,'rapidsms_polls'))
sys.path.append(os.path.join(filedir,'rapidsms_script'))
sys.path.append(os.path.join(filedir,'rapidsms_uregister'))
sys.path.append(os.path.join(filedir,'rapidsms_ureport'))
sys.path.append(os.path.join(filedir,'rapidsms_xforms_src'))
sys.path.append(os.path.join(filedir,'rapidsms_healthmodels'))
sys.path.append(os.path.join(filedir,'django_eav'))
sys.path.append(os.path.join(filedir,'rapidsms_logistics'))
sys.path.append(os.path.join(filedir,'rapidsms_alerts'))
sys.path.append(os.path.join(filedir,'..','lib','dimagi-utils'))
sys.path.append(os.path.join(filedir,'uganda_common'))
sys.path.append(os.path.join(filedir,'rapidsms_unregister'))
sys.path.append(os.path.join(filedir,'rapidsms_emis'))

if __name__ == "__main__":
    execute_manager(settings)
