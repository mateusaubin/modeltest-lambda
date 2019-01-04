#!/bin/bash

for filename in $( ls | grep -i -v '.jar\|.phy\|.sh' ); do
  echo ${filename%.*}
  java -jar alter.jar -i $filename -ia -oo Linux -op PhyML -of PHYLIP -o ${filename%.*}.phy
done

