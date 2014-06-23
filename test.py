__author__ = 'minhtuevo'

from django.conf import settings
import os
print "the size of settings:", settings.__sizeof__()
os.system("/edx/app/edxapp/venvs/edxapp/bin/paver test_python")