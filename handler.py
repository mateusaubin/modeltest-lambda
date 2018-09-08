import os
import json
import aws

#libdir = os.path.join(os.getcwd(), 'lib', 'phyml')


def execute(event, context):
    #result = subprocess.run([libdir, "--help"], stdout=subprocess.PIPE)
    # return {
    #    'result': "%s" % result.stdout
    # }
    #import subprocess
    # command = ["./aws", "s3", "sync", "--acl", "public-read", "--delete",
    #           source_dir + "/", "s3://" + to_bucket + "/"]
    #print(subprocess.check_output(command, stderr=subprocess.STDOUT))
    for record in event['Records']:
        sns = aws.SNSInterface(record)
        sns.download()


#upload_path = '/tmp/resized-{}'.format(key)
#s3_client.upload_file(upload_path, '{}resized'.format(bucket), key)

        print('fez algum super processamento')

    return {'msg': "-- THE END -- "}


if bool(os.getenv('IS_LOCAL', False)) & bool(os.getenv('VSCODE', False)):
    with open('sns.json') as f:
        data = json.load(f)
        execute(data, None)
