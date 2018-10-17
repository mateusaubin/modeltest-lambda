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

# Benchmark Script
cd ..
export AWS_DEFAULT_REGION="us-east-2"

cat > benchmark.sh <<"EOF"
#!/bin/bash

time_start=$(date +"%Y-%m-%d_%H-%M-%S")
instance_type=$(curl http://169.254.169.254/latest/meta-data/instance-type)
instance_id=$(curl http://169.254.169.254/latest/meta-data/instance-id)

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
  aws s3 sync results/ s3://mestrado-dev-phyml-fixed/$instance_type-$time_start-$instance_id/ --delete

done


echo === Done: Shutdown ===

sleep 5

# ensure full upload
echo '#s3-sync#' >> results/#_stats.txt
aws s3 sync results/ s3://mestrado-dev-phyml-fixed/$instance_type-$time_start-$instance_id/ --delete

sleep 15

EOF

# Benchmark Execution
chmod +x benchmark.sh
./benchmark.sh
shutdown -h now