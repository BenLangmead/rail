#!/usr/bin/env bash
## A script that:
## (1) Compresses the FASTQs and stages them on S3
## (2) Creates a manifest file for the FASTQs
## (3) Runs Rail-RNA on the 112 datasets on Elastic MapReduce
## $1: directory with fastqs
## $2: where on S3 to stage fastq.gzs
## $3: where on S3 to output Rail results
## $4: path to Rail source directory
## $5: path to manifest file to write (taken in our experiments to be eval/GEUVADIS_112_sim.manifest)
## Requires s3cmd
FASTQDIR=$1
S3STAGED=$2
S3DEST=$3
RAILSRC=$4
MANIFEST=$5
cd $FASTQDIR
ls *.fastq | python -c "import sys
for line in sys.stdin:
    sample_name = list(line.strip().rpartition('_')[0].partition('-'))
    sample_name[0] = sample_name[0] + '_sim'
    print '\t'.join(['${S3STAGED}/' + line.strip() + '.gz', '0', ''.join(sample_name)])" >$MANIFEST
for i in *.fastq; do cat $i | gzip | s3cmd put - $S3STAGED/$i.gz; done
# Submit job to EMR
python $RAILSRC -c 40 -a hg19 -m $MANIFEST -o $S3DEST --core-instance-bid-price 0.11 --master-instance-bid-price 0.11