import boto3
import uuid
import json
import os
from pathlib import Path
import shutil
import logging


class SNSInterface:

    def __del__(self):
        if bool(os.getenv('IS_LOCAL', False)):
            shutil.rmtree(self.tmp_folder)

    def __init__(self, sns_record):
        logging.debug('Processing Record: {}'.format(sns_record))
        self.file_info = self.parse(sns_record)
        self.s3 = boto3.client('s3')

    def parse(self, record):
        message = {'data': record['Sns']['Message'],
                   'run_id': record['Sns']['Subject']}

        phyml_params = json.loads(message['data'])
        filedata = phyml_params.pop('path').split('://')

        logging.info("Received Payload: {}".format(phyml_params))
        self.payload = phyml_params

        return {'bucket': filedata[0], 'key': filedata[1]}

    def download(self):
        tmp_guid = str(uuid.uuid4())
        self.tmp_folder = os.path.join('/tmp', tmp_guid)
        os.mkdir(self.tmp_folder)
        download_path = os.path.join(
            '/tmp', tmp_guid, Path(self.file_info['key']).name)

        logging.info("Downloading to: {}".format(download_path))

        self.s3.download_file(
            self.file_info['bucket'], self.file_info['key'], download_path)

        self.payload["-i"] = download_path
