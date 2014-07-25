#!/usr/bin/env bash
# Set location of Rail repo here
RAILHOME=~/railclones/rail

# Set input/output bucket here -- must be on S3!
BUCKET=s3://rail-experiments

# Submit 20 at 5, 10, and 20 cores
python $RAILHOME/src align elastic -i $BUCKET/GEUV20 -a hg19 -o $BUCKET/GEUVADIS_20_datasets_5_8x_cores_out -c 5 -m $RAILHOME/eval/GEUVADIS_20_samples.manifest --ec2-key-name rail
python $RAILHOME/src align elastic -i $BUCKET/GEUV20 -a hg19 -o $BUCKET/GEUVADIS_20_datasets_10_8x_cores_out -c 10 -m $RAILHOME/eval/GEUVADIS_20_samples.manifest --ec2-key-name rail
python $RAILHOME/src align elastic -i $BUCKET/GEUV20 -a hg19 -o $BUCKET/GEUVADIS_20_datasets_20_8x_cores_out -c 20 -m $RAILHOME/eval/GEUVADIS_20_samples.manifest --ec2-key-name rail

# Submit 40 and 80 at 20 cores
python $RAILHOME/src align elastic -i $BUCKET/GEUV40 -a hg19 -o $BUCKET/GEUVADIS_40_datasets_20_8x_cores_out -c 20 -m $RAILHOME/eval/GEUVADIS_40_samples.manifest --ec2-key-name rail
python $RAILHOME/src align elastic -i $BUCKET/GEUV80 -a hg19 -o $BUCKET/GEUVADIS_80_datasets_20_8x_cores_out -c 20 -m $RAILHOME/eval/GEUVADIS_80_samples.manifest --ec2-key-name rail