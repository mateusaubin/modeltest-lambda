Content-Type: multipart/mixed; boundary="//"
MIME-Version: 1.0

--//
Content-Type: text/cloud-config; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment; filename="cloud-config.txt"

#cloud-config
cloud_final_modules:
- [scripts-user, always]

--//
Content-Type: text/x-shellscript; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment; filename="userdata.txt"

#!/bin/bash

# java
apt update
DEBIAN_FRONTEND=noninteractive apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade
apt install awscli -y
apt-get install default-jre -y

# jModelTest
wget https://github.com/ddarriba/jmodeltest2/files/157117/jmodeltest-2.1.10.tar.gz
tar -xvzf jmodeltest-2.1.10.tar.gz

# Benchmark Dependencies
git clone -n https://github.com/mateusaubin/modeltest-lambda.git --depth 1
cd modeltest-lambda/
git checkout HEAD benchmark-phyles/*.phy

# Environment Variables
export AWS_DEFAULT_REGION="us-east-2"
export MDLTST_INSTANCE_TYPE=$(curl http://169.254.169.254/latest/meta-data/instance-type -s)
export MDLTST_INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id -s)
tmp_time=$(aws ec2 describe-instances --instance-ids $MDLTST_INSTANCE_ID --query "Reservations[*].Instances[*].[LaunchTime]" --output text)
export MDLTST_INSTANCE_LAUNCH=${tmp_time:0:19}

# Benchmark Script
cd ..
cat > benchmark.sh <<"EOF"
#!/bin/bash
set -e # bail-out if anything goes wrong

rm -rf results/
mkdir results/

for filename in $( ls -Sr modeltest-lambda/benchmark-phyles | grep -i '.phy' ); do # -m 3 = limit 3
  
  echo === Start: $filename ===
  
  sleep 5

  java -jar jmodeltest-2.1.10/jModelTest.jar \
  -d modeltest-lambda/benchmark-phyles/$filename \
  -s 203 -f -i -g 4 -n test \
  | tee results/${filename%.*}.txt \
  || break
  
  echo === Done: $filename ===
  
  sleep 5 #flush buffers

  # save execution time
  stat -c '%30n = %x | %y' results/${filename%.*}.txt >> results/#_stats.txt

  # upload partial results
  aws s3 sync results/ s3://mestrado-dev-phyml-fixed/${MDLTST_INSTANCE_TYPE}_${MDLTST_INSTANCE_LAUNCH}_${MDLTST_INSTANCE_ID}/ --delete

done


echo === Done: Shutdown ===

sleep 5

# ensure full upload
echo '#s3-sync#' >> results/#_stats.txt
aws s3 sync results/ s3://mestrado-dev-phyml-fixed/${MDLTST_INSTANCE_TYPE}_${MDLTST_INSTANCE_LAUNCH}_${MDLTST_INSTANCE_ID}/ --delete

sleep 15

EOF

# Benchmark Execution
chmod +x benchmark.sh

                # sync on fail anyway
./benchmark.sh || aws s3 sync results/ s3://mestrado-dev-phyml-fixed/${MDLTST_INSTANCE_TYPE}_${MDLTST_INSTANCE_LAUNCH}_${MDLTST_INSTANCE_ID}/ --delete


shutdown -h now
