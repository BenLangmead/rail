#!/usr/bin/env python

"""
align.py
(first step after preprocessing, before splice.py)

Alignment script for MapReduce pipelines.  Wraps Bowtie.  Has features for (1)
optionally extracting readlets (substrings) of configurable length, at a
configurable interval along the read, (2) optionally truncating reads or
omitting mates.  Each read or readlet is then written to the standard-in
filehandle of an open Bowtie process.  Output from the Bowtie process is parsed
and passed to the standard-out filehandle.  Alignments are in Bowtie format
(not SAM).

Tab-delimited input tuple columns; can be in any of 3 formats:
 Format 1 (unpaired):
  1. Name
  2. Nucleotide sequence
  3. Quality sequence
 Format 2 (paired, 5-column):
  1. Name
  2. Nucleotide sequence for mate 1
  3. Quality sequence for mate 1
  4. Nucleotide sequence for mate 2
  5. Quality sequence for mate 2
 Format 3 (paired, 6-column):
  1. Name for mate 1
  2. Nucleotide sequence for mate 1
  3. Quality sequence for mate 1
  4. Name for mate 2
  5. Nucleotide sequence for mate 2
  6. Quality sequence for mate 2

-Binning/sorting prior to this step:
 (none)

Exons:
Tab-delimited output tuple columns:
1. Partition ID for partition overlapped by interval
2. Interval start
3. Interval end (exclusive)
4. Reference ID
5. Sample label

Introns:
Tab-delimited output tuple columns:
1. Partition ID for partition overlapped by interval (includes strand information)
2. Interval start
3. Interval end (exclusive)
4. Reference ID
5. Sample label
6. Readlet Sequence on 5' site
6. Readlet Sequence on 3' site
"""

import sys
import os
import site
import argparse
import threading
import string
import time
timeSt = time.clock()

base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
site.addsitedir(os.path.join(base_path, "bowtie"))
site.addsitedir(os.path.join(base_path, "read"))
site.addsitedir(os.path.join(base_path, "sample"))
site.addsitedir(os.path.join(base_path, "interval"))
site.addsitedir(os.path.join(base_path, "manifest"))
site.addsitedir(os.path.join(base_path, "alignment"))
site.addsitedir(os.path.join(base_path, "fasta"))


import bowtie
import readlet
import sample
import manifest
import interval
import partition
import eddist
import nw
import fasta

ninp = 0               # # lines input so far
nout = 0               # # lines output so far
pe = False
discardMate = None
lengths = dict()       # read lengths after truncation
rawLengths = dict()    # read legnths prior to truncation
qualCnts = dict()      # quality counts after adjustments
rawQualCnts = dict()   # quality counts before adjustments
qualAdd = None         # amt to add to qualities
truncateAmt = None     # amount to truncate reads
truncateTo = None      # amount to truncate reads

readletize = None      # if we're going to readletize, 

xformReads = qualAdd is not None or truncateAmt is not None or truncateTo is not None 

parser = argparse.ArgumentParser(description=\
    'Align reads using Bowtie, usually as the map step in a Hadoop program.')
parser.add_argument(\
    '--refseq', type=str, required=True,
    help='The fasta sequence of the reference genome. The fasta index of the '
         'reference genome is also required to be built via samtools')
parser.add_argument(\
    '--splice_overlap', type=int, default=10,
    help='The overlap length of spanning readlets when evaluating splice junctions')
parser.add_argument(\
    '--faidx', type=str, required=True, help='Fasta index file')

bowtie.addArgs(parser)
readlet.addArgs(parser)
manifest.addArgs(parser)
partition.addArgs(parser)

parser.add_argument(\
    '--v2', action='store_const', const=True, default=False, help='New readlet handling')

args = parser.parse_args()
binsz = partition.binSize(args)

if not os.path.exists(args.refseq):
    raise RuntimeError("No such --refseq file: '%s'" % args.refseq)
if not os.path.exists(args.faidx):
    raise RuntimeError("No such --faidx file: '%s'" % args.faidx)

fnh = fasta.fasta(args.refseq)

def xformRead(seq, qual):
    # Possibly truncate and/or modify quality values
    # TODO: not implemented yet!
    newseq, newqual = "", ""
    if truncateAmt is not None:
        pass
    if truncateTo is not None:
        pass
    if qualAdd is not None:
        pass
    return newseq, newqual

_revcomp_trans = string.maketrans("ACGT", "TGCA")
def revcomp(s):
    return s[::-1].translate(_revcomp_trans)

bowtieOutDone = threading.Event()
bowtieErrDone = threading.Event()

def composeReadletAlignments(rdnm, rdals, rdseq):
    
    # TODO: We include strand info with introns, but not exons.  We might want
    # to include for both for the case where the RNA-seq protocol is stranded.
    
    global nout
    # Add this interval to the flattened interval collection for current read
    ivals = {}
    positions = dict()  #stores readlet number based keyed by position
    for rdal in rdals:
        refid, fw, refoff0, seqlen, rlet_nm = rdal
        refoff0, seqlen, rlet_nm = int(refoff0), int(seqlen), int(rlet_nm)
        # Remember begin, end offsets for readlet w/r/t 5' end of the read
        positions[(refid, fw, refoff0)] = rlet_nm * args.readletIval
        positions[(refid, fw, refoff0 + seqlen)] = rlet_nm * args.readletIval + seqlen
        if (refid, fw) not in ivals:
            ivals[(refid, fw)] = interval.FlatIntervals()
        ivals[(refid, fw)].add(interval.Interval(refoff0, refoff0 + seqlen))
    
    for kfw in ivals.iterkeys(): # for each chromosome covered by >= 1 readlet
        k, fw = kfw
        in_end, in_start = -1, -1
        for iv in sorted(iter(ivals[kfw])): # for each covered interval, left-to-right
            st, en = iv.start, iv.end
            assert en > st
            assert st >= 0 and en >= 0
            if in_end == -1 and in_start >= 0:
                in_end = st
                
            if in_start == -1:
                in_start = en
            if in_start >= 0 and in_end >= 0:
                
                if (in_end > in_start) and (in_end-in_start) < (args.readletLen): #drops all introns less than a readlet length
                    # Take into consideration the fw variable.  Need to apply
                    # reverse complement if not on forward strand.
                    refseq = fnh.fetch_sequence(k,in_start + 1, in_end + 1) # Sequence from genome         
                    region_st = positions[(k, fw, in_start)]
                    region_end = positions[(k, fw, in_end)]
                    rdsubseq = rdseq[region_st:region_end]
                    if not fw:
                        rdsubseq = revcomp(rdsubseq)
                    score = nw.needlemanWunsch(refseq, rdsubseq, nw.exampleCost)
                    # TODO: redo this in terms of percent identity or some
                    # other measure that adapts to length of the missing bit,
                    # not just a raw score 
                    for pt in iter(partition.partition(k, in_start, in_end, binsz)):
                        if score <= 10:
                            print "exon\t%s\t%012d\t%d\t%s\t%s" % (pt, in_start, in_end, k, sample.parseLab(rdnm))
                            nout += 1
                elif (in_end > in_start) and (in_end-in_start)>(args.readletLen):
                    region_st = positions[(k, fw, in_start)]
                    region_end = positions[(k, fw, in_end)]
                    
                    left_flank = rdseq[region_st-args.readletLen-1:region_st-1]
                    left_overlap = rdseq[region_st-1:region_st+args.splice_overlap-1]
                    right_overlap = rdseq[region_end-args.splice_overlap+1:region_end+1]
                    right_flank = rdseq[region_end+1:region_end+args.readletLen+1]
                    if len(left_flank) == len(right_flank): #Trash all junctions spanned by small readlets
                        if not fw:
                            left_flank = revcomp(left_flank)
                            left_overlap = revcomp(left_overlap)
                            right_flank = revcomp(right_flank)
                            right_overlap = revcomp(right_overlap)

                        for pt in iter(partition.partition(k, in_start, in_end, binsz)):
                            fw_char = "+" if fw else "-"
                            print "intron\t%s%s\t%012d\t%d\t%s\t%s\t%s\t%s\t%s\t%s" % (pt, fw_char, in_start, in_end, k, sample.parseLab(rdnm),left_flank,left_overlap,right_flank,right_overlap)
                            nout += 1
                in_start, in_end = en, -1
            # Keep stringing rdid along because it contains the label string
            # Add a partition id that combines the ref id and some function of
            # the offsets
            for pt in iter(partition.partition(k, st, en, binsz)):
                print "exon\t%s\t%012d\t%d\t%s\t%s" % (pt, st, en, k, sample.parseLab(rdnm))
                nout += 1

def bowtieOutReadlets(st):
    ''' Process standard out (stdout) output from Bowtie.  Each line of output
        is another readlet alignment.  We *could* try to perform operations
        over all readlet alignments from the same read here.  Currently, we
        follow this step with an aggregation that bins by read id, then
        operate over bins in splice.py. '''
    global nout
    mem, cnt = {}, {}
    for line in st:
        if line[0] == '@':
            continue
        rdid, flags, refid, refoff1, _, _, _, _, _, seq, _, _ = string.split(line.rstrip(), '\t', 11)
        flags, refoff1 = int(flags), int(refoff1)
        seqlen = len(seq)
        toks = string.split(rdid, ';')
        rdnm = ';'.join(toks[:-3])
        rlet_nm = toks[2]
        cnt[rdnm] = cnt.get(rdnm, 0) + 1
        rdseq = toks[4]
        rdlet_n = int(toks[-2])
        if flags != 4:
            fw = (flags & 16) == 0
            if rdnm not in mem: mem[rdnm] = [ ]
            mem[rdnm].append((refid, fw, refoff1-1, seqlen,rlet_nm))
        if cnt[rdnm] == rdlet_n:
            # Last readlet
            if rdnm in mem:
                composeReadletAlignments(rdnm, mem[rdnm],rdseq)
                del mem[rdnm]
            del cnt[rdnm]
        nout += 1
    assert len(mem) == 0
    assert len(cnt) == 0
    bowtieOutDone.set()

def bowtieOut(st):
    ''' Process standard out (stdout) output from Bowtie.  Each line of output
        is another readlet alignment.  We *could* try to perform operations
        over all readlet alignments from the same read here.  Currently, we
        follow this step with an aggregation that bins by read id, then
        operate over bins in splice.py. '''
    global nout
    for line in st:
        sys.stdout.write(line)
        nout += 1
    bowtieOutDone.set()

def bowtieErr(st):
    ''' Process standard error (stderr) output from Bowtie '''
    for line in st:
        # Print it right back out on sys.stderr
        print >> sys.stderr, line.rstrip()
    bowtieErrDone.set()

if args.v2:
    proc = bowtie.proc(args, sam=True, outHandler=bowtieOutReadlets, errHandler=bowtieErr)
else:
    proc = bowtie.proc(args, sam=False, outHandler=bowtieOut, errHandler=bowtieErr)

for ln in sys.stdin:
    ln = ln.rstrip()
    toks = ln.split('\t')
    ninp += 1
    pair = False
    nm, seq, qual = None, None, None
    nm1, seq1, qual1 = None, None, None
    nm2, seq2, qual2 = None, None, None
    if len(toks) == 3:
        # Unpaired read
        nm, seq, qual = toks
        sample.hasLab(nm, mustHave=True) # check that label is present in name
    elif len(toks) == 5 or len(toks) == 6:
        # Paired-end read
        if len(toks) == 5:
            # 6-token version
            nm1, seq1, qual1, seq2, qual2 = toks
            nm2 = nm1
        else:
            # 5-token version
            nm1, seq1, qual1, nm2, seq2, qual2 = toks
        sample.hasLab(nm1, mustHave=True) # check that label is present in name
        if discardMate is not None:
            # We have been asked to discard one mate or the other
            if discardMate == 1:
                nm, seq, qual = nm2, seq2, qual2 # discard mate 1
            else:
                nm, seq, qual = nm1, seq1, qual1 # discard mate 2
        else:
            pair = True # paired-end read
    else:
        raise RuntimeError("Wrong number of tokens for line: " + ln)
    
    if pair:
        # Paired-end
        if xformReads:
            # Truncate and transform quality values
            seq1, qual1 = xformRead(seq1, qual1)
            seq2, qual2 = xformRead(seq2, qual2)
        if args.readletLen > 0:
            # Readletize
            rlets1 = readlet.readletize(args, nm1, seq1, qual1)
            for i in xrange(0, len(rlets1)):
                nm_rlet, seq_rlet, qual_rlet = rlets1[i]
                if args.v2:
                    proc.stdin.write("%s;%d;%d;%s\t%s\t%s\n" % (nm_rlet, i, len(rlets1),seq1, seq_rlet, qual_rlet))
                else:
                    proc.stdin.write("%s\t%s\t%s\n" % (nm_rlet, seq_rlet, qual_rlet))
            rlets2 = readlet.readletize(args, nm2, seq2, qual2)
            for i in xrange(0, len(rlets2)):
                nm_rlet, seq_rlet, qual_rlet = rlets2[i]
                if args.v2:
                    proc.stdin.write("%s;%d;%d;%s\t%s\t%s\n" % (nm_rlet, i, len(rlets2),seq2, seq_rlet, qual_rlet))
                else:
                    proc.stdin.write("%s\t%s\t%s\n" % (nm_rlet, seq_rlet, qual_rlet))
        else:
            proc.stdin.write("%s\t%s\t%s\t%s\t%s\n" % (nm1, seq1, qual1, seq2, qual2))
    else:
        # Unpaired
        if xformReads:
            # Truncate and transform quality values
            seq, qual = xformRead(seq, qual)
        if args.readletLen > 0:
            # Readletize
            rlets = readlet.readletize(args, nm, seq, qual)
            for i in xrange(0, len(rlets)):
                nm_rlet, seq_rlet, qual_rlet = rlets[i]
                if args.v2:
                    proc.stdin.write("%s;%d;%d;%s\t%s\t%s\n" % (nm_rlet, i, len(rlets), seq, seq_rlet, qual_rlet))
                else:
                    proc.stdin.write("%s\t%s\t%s\n" % (nm_rlet, seq_rlet, qual_rlet))
        else:
            proc.stdin.write("%s\t%s\t%s\n" % (nm, seq, qual))

# Close and flush STDIN.
proc.stdin.close()

# Wait until the threads processing stdout and stderr are done.

# Close stdout and stderr
print >>sys.stderr, "Waiting for Bowtie stdout processing thread to finish"
bowtieOutDone.wait()
print >>sys.stderr, "Waiting for Bowtie stderr processing thread to finish"
bowtieErrDone.wait()

proc.stdout.close()
proc.stderr.close()

# Done
timeEn = time.clock()
print >>sys.stderr, "DONE with align.py; in/out = %d/%d; time=%0.3f secs" % (ninp, nout, timeEn-timeSt)
