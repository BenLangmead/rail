#!/usr/bin/env python
"""
spliced_read_recovery_performance.py

Outputs precision, recall, and related performance measurements of a spliced
aligner given a Flux-like BED file T with true spliced alignments and a SAM
file Y with the aligner's spliced alignments (read from stdin). Only reads that
overlap introns in the relevant (true) and retrieved (aligner result) datasets
are considered. Secondary alignments from the SAM input are ignored.

If a coverage threshold is specified with -c, only reads that overlap at least
one intron whose TRUE coverage is <= -c are considered.

THIS FILE DEPENDS ON DOOPLICITY AND RAIL; don't move it in the Rail repo.

Output (written to stdout)
----------------------------
Two columns delimited by tabs, where the first column characterizes the numbers
in the second column. The first column is given below.

relevant instances
retrieved instances
intersection [of relevant and retrieved instances]
precision
recall
"""

import sys
import site
import os
import re
from collections import defaultdict

base_path = os.path.dirname(os.path.dirname(
                        os.path.realpath(__file__))
                    )
utils_path = os.path.join(base_path, 'src', 'rna', 'utils')
src_path = os.path.join(base_path, 'src')

site.addsitedir(utils_path)
site.addsitedir(src_path)

from cigar_parse import indels_introns_and_exons
from dooplicity.tools import xstream

def dummy_md_index(cigar):
    """ Creates dummy MD string from CIGAR in case of missing MD.

        cigar: cigar string

        Return value: dummy MD string
    """
    cigar = re.split(r'([MINDS])', cigar)[:-1]
    cigar_index = 0
    max_cigar_index = len(cigar)
    md = []
    while cigar_index != max_cigar_index:
        if cigar[cigar_index] == 0:
            cigar_index += 2
            continue
        if cigar[cigar_index+1] == 'M':
            try:
                if type(md[-1]) is int:
                    md[-1] += int(cigar[cigar_index])
                else:
                    md.append(int(cigar[cigar_index]))
            except IndexError:
                md.append(int(cigar[cigar_index]))
            cigar_index += 2
        elif cigar[cigar_index+1] in 'SIN':
            cigar_index += 2
        elif cigar[cigar_index+1] == 'D':
            md.extend(['^', 'A'*int(cigar[cigar_index])])
            cigar_index += 2
        else:
            raise RuntimeError(
                        'Accepted CIGAR characters are only in [MINDS].'
                    )
    return ''.join(str(el) for el in md)

def write_read_introns_from_bed_stream(bed_stream, output_stream,
                                        intron_counts,
                                        generous=False):
    """ Writes output that maps QNAMES to introns overlapped.

        bed_stream: input stream containing lines of a BED file characterizing
            splice junctions.
        output_stream: where to write output. Each line takes the form:
            <read name><TAB><sorted list of intron starts and ends>
            <TAB>['t' for 'true']
        intron_counts: defaultdict(int) that counts number of reads overlapping
            intron
        generous: True iff QNAMES should have the last two chars cut off

        No return value.
    """
    for line in bed_stream:
        introns = set()
        tokens = line.rstrip().split('\t')
        if len(tokens) < 12:
            continue
        chrom = tokens[0]
        chrom_start = int(tokens[1])
        chrom_end = int(tokens[2])
        name = tokens[3]
        block_sizes = tokens[10].split(',')
        block_starts = tokens[11].split(',')
        # Handle trailing commas
        try:
            int(block_sizes[-1])
        except ValueError:
            block_sizes = block_sizes[:-1]
        try:
            int(block_starts[-1])
        except ValueError:
            block_starts = block_starts[:-1]
        block_count = len(block_sizes)
        if block_count < 2:
            # No introns
            continue
        assert block_count == len(block_starts)
        junctions = []
        # First block characterizes junction on left side of intron
        junctions.append(chrom_start + int(block_starts[0]) 
                                + int(block_sizes[0]))
        for i in xrange(1, block_count - 1):
            # Any intervening blocks characterize two junctions
            intron_start = chrom_start + int(block_starts[i])
            junctions.append(intron_start)
            junctions.append(intron_start + int(block_sizes[i]))
        # Final block characterizes junction on right side of intron
        junctions.append(chrom_start + int(block_starts[-1]))
        for i in xrange(len(junctions)/2):
            introns.add((junctions[2*i] + 1, junctions[2*i+1] + 1))
        if introns:
            print >>output_stream, '%s\t%s\tt' \
                % (name[:-2] if generous else name,
                    '\t'.join(
                            [chrom + ';'.join(['']
                                + [str(bound) for bound in intron])
                             for intron in sorted(list(introns))]
                         ))
        for intron in introns:
            intron_counts[chrom
                    + ';'.join([''] + [str(bound) for bound in intron])
                ] += 1

def write_read_introns_from_sam_stream(sam_stream, output_stream):
    """ Writes output that maps QNAMES to introns overlapped.

        sam_stream: where to find retrieved alignments in SAM form
        output_stream: where to write output. Each line takes the form:
            <read name><TAB>RNAME<TAB><sorted list of intron starts and ends>
            <TAB>['r' for 'retrieved']

        No return value.
    """
    for line in sam_stream:
        if line[0] == '@': continue
        try:
            tokens = line.strip().split('\t')
            flag = int(tokens[1])
            if flag & 4:
                continue
            name = tokens[0]
            rname = tokens[2]
            cigar = tokens[5]
            pos = int(tokens[3])
            seq = tokens[9]
            flag = int(tokens[1])
            if 'N' not in cigar or flag & 256:
                continue
            #md = [token[5:] for token in tokens if token[:5] == 'MD:Z:'][0]
            _, _, introns, _ = indels_introns_and_exons(cigar,
                                        dummy_md_index(cigar), pos, seq)
            introns = [intron[:2] for intron in introns]
            print >>output_stream, '%s\t%s\tr' \
                % (name, '\t'.join(
                        [rname 
                          + ';'.join([''] + [str(bound) for bound in intron])
                          for intron in sorted(list(introns))]
                    ))
        except IndexError:
            print >>sys.stderr, ('Error found on line: ' + line)
            raise

if __name__ == '__main__':
    import argparse
    # Print file's docstring if -h is invoked
    parser = argparse.ArgumentParser(description=__doc__, 
            formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-t', '--true-introns-bed', type=str, required=True, 
        help='Full path of BED file containing true introns')
    parser.add_argument('-g', '--generous', action='store_const', const=True,
        default=False,
        help='TopHat/STAR cut off /1s and /2s from read names, even in '
             'unpaired mode. This loses information. In generous mode, '
             'this script provides extremely tight upper bounds on '
             'precision and recall for TopHat/STAR')
    parser.add_argument('-c', '--coverage-threshold', type=int,
        required=False, default=None,
        help='Consider only reads that overlap at least '
             'one intron whose TRUE coverage is <= -c')
    args = parser.parse_args(sys.argv[1:])
    from tempdel import remove_temporary_directories
    import tempfile
    import atexit
    temp_dir_path = tempfile.mkdtemp()
    atexit.register(remove_temporary_directories, [temp_dir_path])
    combined_file = os.path.join(temp_dir_path, 'combined.temp')
    intron_counts = defaultdict(int)
    with open(combined_file, 'w') as combined_stream:
        with open(args.true_introns_bed) as true_introns_bed_stream:
            write_read_introns_from_bed_stream(true_introns_bed_stream,
                                                combined_stream,
                                                intron_counts,
                                                generous=args.generous)
        write_read_introns_from_sam_stream(sys.stdin, combined_stream)
    import subprocess
    sorted_combined_file = os.path.join(temp_dir_path, 'combined.sorted.temp')
    subprocess.check_call(' '.join(['sort -k1,1', combined_file, 
                                    '>', sorted_combined_file]),
                            bufsize=-1, shell=True)
    relevant = 0
    retrieved = 0
    relevant_and_retrieved = 0
    with open(sorted_combined_file) as sorted_combined_stream:
        for (name,), xpartition in xstream(sorted_combined_stream, 1):
            relevant_and_retrieved_instances = list(xpartition)
            if args.generous:
                ts = [instance[:-1] for instance 
                        in relevant_and_retrieved_instances
                        if instance[-1] == 't'
                        and (args.coverage_threshold is None
                             or any(
                        [intron_counts[intron] <= args.coverage_threshold
                         for intron in instance[:-1]]
                         ))]
                rs = [instance[:-1] for instance 
                        in relevant_and_retrieved_instances
                        if instance[-1] == 'r'
                        and (args.coverage_threshold is None
                             or any(
                        [intron_counts[intron] <= args.coverage_threshold
                         for intron in instance[:-1]]
                         ))]
                relevant += len(ts)
                retrieved += len(rs)
                for r in rs:
                    if r in ts:
                        relevant_and_retrieved += 1
            else:
                relevant_and_retrieved_instances = [
                        instance for instance
                        in relevant_and_retrieved_instances
                        if (args.coverage_threshold is None
                             or any(
                           [intron_counts[intron] <= args.coverage_threshold
                            for intron in instance[:-1]]
                         ))
                    ]
                relevant_and_retrieved_instance_count = \
                    len(relevant_and_retrieved_instances)
                if relevant_and_retrieved_instance_count == 2:
                    relevant += 1
                    retrieved += 1
                    if relevant_and_retrieved_instances[0][:-1] \
                        == relevant_and_retrieved_instances[1][:-1]:
                        relevant_and_retrieved += 1
                    else:
                        print >>sys.stderr, relevant_and_retrieved_instances
                elif relevant_and_retrieved_instance_count == 1:
                    print >>sys.stderr, relevant_and_retrieved_instances
                    if relevant_and_retrieved_instances[0][-1] == 't':
                        relevant += 1
                    else:
                        assert relevant_and_retrieved_instances[0][-1] == 'r'
                        retrieved += 1
                else:
                    assert relevant_and_retrieved_instance_count == 0
    precision = float(relevant_and_retrieved) / retrieved
    recall = float(relevant_and_retrieved) / relevant
    print 'relevant instances\t%d' % relevant
    print 'retrieved instances\t%d' % retrieved
    print 'intersection\t%d' % relevant_and_retrieved
    print 'precision\t%.9f' % precision
    print 'recall\t%.9f' % recall