import json
import subprocess
import boto3
import os
import sys
import uuid
from pathlib import Path  
import time
import shutil

s3 = boto3.client('s3')
libdir = os.path.join(os.getcwd(), 'lib', 'phyml')

def execute(event, context):
    #result = subprocess.run([libdir, "--help"], stdout=subprocess.PIPE)
    #return { 
    #    'result': "%s" % result.stdout 
    #}
    #import subprocess
    #command = ["./aws", "s3", "sync", "--acl", "public-read", "--delete",
    #           source_dir + "/", "s3://" + to_bucket + "/"]
    #print(subprocess.check_output(command, stderr=subprocess.STDOUT))
    for record in event['Records']:

        # PARSE
        message = { 'data' : record['Sns']['Message'], 'run_id' : record['Sns']['Subject'] }
        payload = json.loads(message['data'])
        filedata = payload.pop('path').split('://')
        finfo = {'bucket':filedata[0], 'key':filedata[1]}

        # DOWNLOAD
        tmp_guid = str(uuid.uuid4())
        tmp_folder = os.path.join('/tmp', tmp_guid)
        os.mkdir(tmp_folder)
        download_path = os.path.join('/tmp', tmp_guid, Path(finfo['key']).name)

        print(download_path)
        print(payload)

        s3.download_file(finfo['bucket'], finfo['key'], download_path)
      

#upload_path = '/tmp/resized-{}'.format(key)
#s3_client.upload_file(upload_path, '{}resized'.format(bucket), key)

        if bool(os.getenv('IS_LOCAL', False)):
            time.sleep(1)
            print('delete temp')
            shutil.rmtree(tmp_folder)

        print('fez algum super processamento')

    return { 'msg': "-- THE END -- " }


if bool(os.getenv('IS_LOCAL', False)) & bool(os.getenv('VSCODE', False)):
    with open('sns.json') as f:
        data = json.load(f)
        execute(data,None)