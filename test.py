__author__ = 'minhtuevo'

from django.conf import settings
import os
print "the total size of settings:", settings.__sizeof__()

print os.environ
os.environ['PATH'] += ":/edx/app/edxapp/venvs/edxapp/bin"
print os.environ['PATH']
# os.system("/edx/app/edxapp/venvs/edxapp/bin/activate")
os.system
os.system("paver test_python")