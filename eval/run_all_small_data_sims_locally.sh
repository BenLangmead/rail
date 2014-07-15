#!/usr/bin/env bash

# Select two sample names for analysis. See generate_bioreps.py for how sample data was generated.
SAMPLE1=NA18861.1.M_120209_2
SAMPLE2=NA18508.1.M_111124_1

# Specify data directory; fastqs should be of the form [SAMPLE NAME]_sim.fastq
DATADIR=/scratch0/langmead-fs1/geuvadis_sim

## Specify locations of executables
# Use version 2.0.12 of TopHat; wrapped version 2.2.2 of Bowtie2
TOPHAT=/scratch0/langmead-fs1/shared/tophat-2.0.12.Linux_x86_64/tophat2
# Use version 2.3.0e of STAR
STAR=/scratch0/langmead-fs1/shared/STAR_2.3.0e.Linux_x86_64/STAR
# Use version 0.1.0 of Rail-RNA; wrapped version 2.2.2 of Bowtie2
# Specify Python executable/loc of get_junctions.py; PyPy 2.2.1 was used
PYTHON=pypy
RAILHOME=/scratch0/langmead-fs1/rail
RAILRNA=$PYTHON\ $RAILHOME/src

# Specify number of parallel processes for each program
CORES=32

# Specify output directory
MAINOUTPUT=/scratch0/langmead-fs1/geuvadis_sim/local_out

# Specify log file for recording times
TIMELOG=$MAINOUTPUT/small_data_times.log

## Specify locations of reference-related files
## See create_indexes.sh for index creation script
# Bowtie indexes
BOWTIE1IDX=/scratch0/langmead-fs1/indexes_for_paper/genome
BOWTIE2IDX=/scratch0/langmead-fs1/indexes_for_paper/genome
# STAR index
STARIDX=/scratch0/langmead-fs1/indexes_for_paper/star
# Overhang length for STAR; this should be max read length - 1
OVERHANG=75

## Specify location of annotation
# This is Gencode v12, which may be obtained at ftp://ftp.sanger.ac.uk/pub/gencode/release_12/gencode.v12.annotation.gtf.gz
ANNOTATION=/scratch0/langmead-fs1/geuvadis_sim/gencode.v12.annotation.gtf

## STAR requires its own annotation format that lists introns directly; conversion is done by get_junctions.py
# Build STAR junction index from GTF
STARANNOTATION=$OUTPUT/junctions_for_star.txt
echo 'Building annotation from GTF for STAR...'
cat $ANNOTATION | $PYTHON $RAILHOME/eval/get_junctions.py >$STARANNOTATION

## Where Feb 2009 hg19 chromosome files are located; download them at http://hgdownload.cse.ucsc.edu/goldenPath/hg19/bigZips/chromFa.tar.gz
# These are here because it's necessary to build a new STAR index for its annotation protocols
FADIR=/scratch0/langmead-fs1/shared/references/hg19/fasta

# Flux outputs paired-end reads in one file; split files here
echo 'Splitting Flux FASTQs...'
for SAMPLE in {$SAMPLE1,$SAMPLE2}
do
	awk 'NR % 8 < 4' $DATADIR/$SAMPLE_sim.fastq > $DATADIR/$SAMPLE_sim_left.fastq
	awk 'NR % 8 >= 4' $DATADIR/$SAMPLE_sim.fastq > $DATADIR/$SAMPLE_sim_right.fastq
done

# Create output directories
mkdir -p $MAINOUTPUT
cd $MAINOUTPUT
for SAMPLE in {$SAMPLE1,$SAMPLE2}
do
	mkdir -p $SAMPLE
	cd $SAMPLE
	mkdir -p tophat
	mkdir -p star
	mkdir -p rail
done

# Run simulations
for SAMPLE in {$SAMPLE1,$SAMPLE2}
do
	OUTPUT=$MAINOUTPUT/$SAMPLE
	echo 'Running TopHat on sample $SAMPLE with no annotation and in single-end mode...'
	echo '#$SAMPLE TopHat noann single' >>$TIMELOG
	time ($TOPHAT -o $OUTPUT/tophat/noann_single -p $CORES $BOWTIE2IDX $DATADIR/$SAMPLE_sim.fastq) 2>>$TIMELOG
	echo 'Running TopHat on sample $SAMPLE with no annotation and in paired-end mode...'
	echo '#$SAMPLE TopHat noann paired' >>$TIMELOG
	time ($TOPHAT -o $OUTPUT/tophat/noann_paired -p $CORES $BOWTIE2IDX $DATADIR/$SAMPLE_sim_left.fastq $DATADIR/$SAMPLE_sim_right.fastq) 2>>$TIMELOG
	echo 'Running TopHat on sample $SAMPLE with annotation and in single-end mode...'
	echo '#$SAMPLE TopHat ann single' >>$TIMELOG
	time ($TOPHAT -o $OUTPUT/tophat/ann_single -G $ANNOTATION -p $CORES $BOWTIE2IDX $DATADIR/$SAMPLE_sim.fastq) 2>>$TIMELOG
	echo 'Running TopHat on sample $SAMPLE with annotation and in paired-end mode...'
	echo '#$SAMPLE TopHat ann paired' >>$TIMELOG
	time ($TOPHAT -o $OUTPUT/tophat/ann_paired -G $ANNOTATION -p $CORES $BOWTIE2IDX $DATADIR/$SAMPLE_sim_left.fastq $DATADIR/$SAMPLE_sim_right.fastq) 2>>$TIMELOG
	# STAR protocols for execution are described on pp. 43-44 of the supplement of the RGASP spliced alignment paper
	# (http://www.nature.com/nmeth/journal/v10/n12/extref/nmeth.2722-S1.pdf)
	echo 'Running STAR on sample $SAMPLE with no annotation and in single-end mode...'
	echo '#$SAMPLE STAR 1-pass noann single' >>$TIMELOG
	mkdir -p $OUTPUT/star/noann_single_1pass
	cd $OUTPUT/star/noann_single_1pass
	time ($STAR --genomeDir $STARIDX --readFilesIn $DATADIR/$SAMPLE_sim.fastq --runThreadN $CORES) 2>>$TIMELOG
	echo 'Running STAR on sample $SAMPLE with no annotation and in paired-end mode...'
	echo '#$SAMPLE STAR 1-pass noann paired' >>$TIMELOG
	mkdir -p $OUTPUT/star/noann_paired_1pass
	cd $OUTPUT/star/noann_paired_1pass
	time ($STAR --genomeDir $STARIDX --readFilesIn $DATADIR/$SAMPLE_sim_left.fastq $DATADIR/$SAMPLE_sim_right.fastq --runThreadN $CORES) 2>>$TIMELOG
	echo 'Creating new STAR index for sample $SAMPLE including splice junctions...'
	echo '##SAMPLE STAR index pre-1-pass ann' 2>>$TIMELOG
	STARANNIDX=$OUTPUT/star/new_idx
	mkdir -p $STARANNIDX
	# Use --sjdbOverhang 75 because reads are 76 bases long! See p. 3 of STAR manual for details.
	time ($STAR --runMode genomeGenerate --genomeDir $STARANNIDX --genomeFastaFiles $FADIR/chr{1..22}.fa $FADIR/chr{X,Y,M}.fa \
			--runThreadN $CORES --sjdbFileChrStartEnd $STARANNOTATION --sjdbOverhang $OVERHANG) 2>>$TIMELOG
	echo 'Running STAR on sample $SAMPLE with annotation and in single-end mode...'
	echo '#$SAMPLE STAR 1-pass ann single' >>$TIMELOG
	mkdir -p $OUTPUT/star/ann_single_1pass
	cd $OUTPUT/star/ann_single_1pass
	time ($STAR --genomeDir $STARANNIDX --readFilesIn $DATADIR/$SAMPLE_sim.fastq --runThreadN $CORES) 2>>$TIMELOG
	echo 'Running STAR on sample $SAMPLE with annotation and in paired-end mode...'
	echo '#$SAMPLE STAR 1-pass ann paired' >>$TIMELOG
	mkdir -p $OUTPUT/star/ann_paired_1pass
	cd $OUTPUT/star/ann_paired_1pass
	time ($STAR --genomeDir $STARANNIDX --readFilesIn $DATADIR/$SAMPLE_sim_left.fastq $DATADIR/$SAMPLE_sim_right.fastq --runThreadN $CORES) 2>>$TIMELOG
	echo 'Creating new STAR index for sample $SAMPLE with no annotation and in single-end mode...'
	echo '#$SAMPLE STAR 1-pass noann single index' >>$TIMELOG
	STARIDXNOANNSINGLE=$OUTPUT/star/noann_single_idx
	mkdir -p $STARIDXNOANNSINGLE
	time ($STAR --runMode genomeGenerate --genomeDir $STARIDXNOANNSINGLE --genomeFastaFiles $FADIR/chr{1..22}.fa $FADIR/chr{X,Y,M}.fa \
			--sjdbFileChrStartEnd $OUTPUT/star/noann_single_1pass/SJ.out.tab --sjdbOverhang $OVERHANG --runThreadN $CORES) 2>>$TIMELOG
	echo 'Creating new STAR index for sample $SAMPLE with no annotation and in paired-end mode...'
	echo '#$SAMPLE STAR 1-pass noann paired index' >>$TIMELOG
	STARIDXNOANNPAIRED=$OUTPUT/star/noann_paired_idx
	mkdir -p $STARIDXNOANNPAIRED
	time ($STAR --runMode genomeGenerate --genomeDir $STARIDXNOANNPAIRED --genomeFastaFiles $FADIR/chr{1..22}.fa $FADIR/chr{X,Y,M}.fa \
			--sjdbFileChrStartEnd $OUTPUT/star/noann_paired_1pass/SJ.out.tab --sjdbOverhang $OVERHANG --runThreadN $CORES) 2>>$TIMELOG
	echo 'Creating new STAR index for sample $SAMPLE with annotation and in single-end mode...'
	echo '#$SAMPLE STAR 1-pass noann single index' >>$TIMELOG
	STARIDXANNSINGLE=$OUTPUT/star/ann_single_idx
	mkdir -p $STARIDXANNSINGLE
	time ($STAR --runMode genomeGenerate --genomeDir $STARIDXANNSINGLE --genomeFastaFiles $FADIR/chr{1..22}.fa $FADIR/chr{X,Y,M}.fa \
			--sjdbFileChrStartEnd $OUTPUT/star/ann_single_1pass/SJ.out.tab --sjdbOverhang $OVERHANG --runThreadN $CORES) 2>>$TIMELOG
	echo 'Creating new STAR index for sample $SAMPLE with annotation and in paired-end mode...'
	echo '#$SAMPLE STAR 1-pass noann paired index' >>$TIMELOG
	STARIDXANNPAIRED=$OUTPUT/star/ann_paired_idx
	mkdir -p $STARIDXANNPAIRED
	time ($STAR --runMode genomeGenerate --genomeDir $STARIDXANNPAIRED --genomeFastaFiles $FADIR/chr{1..22}.fa $FADIR/chr{X,Y,M}.fa \
			--sjdbFileChrStartEnd $OUTPUT/star/ann_paired_1pass/SJ.out.tab --sjdbOverhang $OVERHANG --runThreadN $CORES) 2>>$TIMELOG
	echo 'Running second pass of STAR on sample $SAMPLE with no annotation and in single-end mode...'
	echo '#$SAMPLE STAR 2-pass noann single' >>$TIMELOG
	mkdir -p $OUTPUT/star/noann_single_2pass
	cd $OUTPUT/star/noann_single_2pass
	time ($STAR --genomeDir $STARIDXNOANNSINGLE --readFilesIn $DATADIR/$SAMPLE_sim.fastq --runThreadN $CORES) 2>>$TIMELOG
	echo 'Running second pass of STAR on sample $SAMPLE with no annotation and in paired-end mode...'
	echo '#$SAMPLE STAR 2-pass noann paired' >>$TIMELOG
	mkdir -p $OUTPUT/star/noann_paired_2pass
	cd $OUTPUT/star/noann_paired_2pass
	time ($STAR --genomeDir $STARIDXNOANNPAIRED --readFilesIn $DATADIR/$SAMPLE_sim_left.fastq $DATADIR/$SAMPLE_sim_right.fastq --runThreadN $CORES) 2>>$TIMELOG
	echo 'Running second pass of STAR on sample $SAMPLE with annotation and in single-end mode...'
	echo '#$SAMPLE STAR 2-pass ann single' >>$TIMELOG
	mkdir -p $OUTPUT/star/ann_single_2pass
	cd $OUTPUT/star/ann_single_2pass
	time ($STAR --genomeDir $STARIDXANNSINGLE --readFilesIn $DATADIR/$SAMPLE_sim.fastq --runThreadN $CORES) 2>>$TIMELOG
	echo 'Running second pass of STAR on sample $SAMPLE with annotation and in paired-end mode...'
	echo '#$SAMPLE STAR 2-pass ann paired' >>$TIMELOG
	mkdir -p $OUTPUT/star/ann_paired_2pass
	cd $OUTPUT/star/ann_paired_2pass
	time ($STAR --genomeDir $STARIDXANNPAIRED --readFilesIn $DATADIR/$SAMPLE_sim_left.fastq $DATADIR/$SAMPLE_sim_right.fastq --runThreadN $CORES) 2>>$TIMELOG
	echo 'Running Rail-RNA on sample $SAMPLE...'
	echo '#$SAMPLE Rail-RNA'
	# Write manifest file
	echo -e $DATADIR/$SAMPLE_sim.fastq'\t0\t'$SAMPLE'-0-0' >$MAINOUTPUT/$SAMPLE.manifest
	time ($RAILRNA go local -m $MAINOUTPUT/$SAMPLE.manifest -o -1 $BOWTIE1IDX -2 $BOWTIE2IDX) 2>>$TIMELOG
done