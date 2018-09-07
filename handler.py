import json
import os
import subprocess

libdir = os.path.join(os.getcwd(), 'lib', 'phyml')

def execute(event, context):
    result = subprocess.run([libdir, "--help"], stdout=subprocess.PIPE)
    return { 
        'result': "%s" % result.stdout 
    }
