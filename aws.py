import boto3
import uuid
import json
import os
from pathlib import Path
import shutil


class SNSInterface:

    def __del__(self):
        if bool(os.getenv('IS_LOCAL', False)):
            print('delete temp')
            shutil.rmtree(self.tmp_folder)
        print("goodbye temp data")

    def __init__(self, sns_record):
        self.file_info = self.parse(sns_record)
        self.s3 = boto3.client('s3')

    @staticmethod
    def parse(record):
        message = {'data': record['Sns']['Message'],
                   'run_id': record['Sns']['Subject']}
        payload = json.loads(message['data'])
        filedata = payload.pop('path').split('://')
        finfo = {'bucket': filedata[0], 'key': filedata[1]}

        print(payload)
        return finfo

    def download(self):
        tmp_guid = str(uuid.uuid4())
        self.tmp_folder = os.path.join('/tmp', tmp_guid)
        os.mkdir(self.tmp_folder)
        download_path = os.path.join(
            '/tmp', tmp_guid, Path(self.file_info['key']).name)

        print(download_path)
        self.s3.download_file(
            self.file_info['bucket'], self.file_info['key'], download_path)
