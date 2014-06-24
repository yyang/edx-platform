__author__ = 'minhtuevo'

from django.conf import settings
import os
print "the total size of settings:", settings.__sizeof__()

print os.environ
os.environ['PATH'] += ":/edx/app/edxapp/venvs/edxapp/bin"
print os.environ['PATH']
print "i see here"
print "launching firefox"
os.system("firefox")
print "firefox launched"