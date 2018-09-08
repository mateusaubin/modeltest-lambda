import boto3
import json
import os
from pathlib import Path
import shutil
import logging


class SNSInterface:

    def __del__(self):
        if bool(os.getenv('IS_LOCAL', False)):
            shutil.rmtree(self.tmp_folder)

    def __init__(self, sns_message, correlation_id):
        logging.debug('Processing Message: {}'.format(sns_message))
        self._correlation_id = correlation_id
        self.file_info = self.parse(sns_message)
        self.s3 = boto3.client('s3')

    def parse(self, sns_message):
        phyml_params = json.loads(sns_message)
        filedata = phyml_params.pop('path').split('://')

        logging.info("Received Payload: {}".format(phyml_params))
        self.payload = phyml_params

        return {'bucket': filedata[0], 'key': filedata[1]}

    def download(self):
        self.tmp_folder = os.path.join('/tmp', self._correlation_id)
        os.mkdir(self.tmp_folder)
        download_path = os.path.join(
            '/tmp', self._correlation_id, Path(self.file_info['key']).name)

        logging.info("Downloading to: {}".format(download_path))

        self.s3.download_file(
            self.file_info['bucket'], self.file_info['key'], download_path)

        self.payload["-i"] = download_path
