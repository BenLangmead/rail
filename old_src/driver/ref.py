"""
ref.py

Responsible for replacing reference archive-related placeholders in mapper and
reducer commands.  E.g. REF_FASTA, REF_BOWTIE_INDEX.

%REF_BOWTIE_INDEX%: Directory with genome.*.ebwt
"""

import os

# Reference file subdirs when reference directory is a Rail-RNA archive
refLoc = { \
    'REF_BOWTIE_INDEX'   : 'index/genome',
    'REF_BOWTIE2_INDEX'  : 'index/genome',
    'REF_INTRON_INDEX'   : 'index/intron',
    'REF_GTF'            : 'gtf/genes.gtf' }

# Reference file subdirs when reference directory is an iGenomes archive
iGenomesLoc = { \
    'REF_BOWTIE_INDEX'  : 'Sequence/BowtieIndex/genome',
    'REF_BOWTIE2_INDEX' : 'Sequence/Bowtie2Index/genome',
    'REF_INTRON_INDEX'  : 'index/intron',
    'REF_GTF'           : 'Annotation/Genes/genes.gtf' }

def checkBowtieIndex(base, iGenomes=False):
    # Check existence of all the .ebwt files
    loc = iGenomesLoc if iGenomes else refLoc
    for ext in [ '.1.ebwt', '.2.ebwt', '.3.ebwt', '.4.ebwt', '.rev.1.ebwt', '.rev.2.ebwt']:
        ifn = '/'.join([base, loc['REF_BOWTIE_INDEX'] + ext])
        if not os.path.exists(ifn):
            raise RuntimeError('No such Bowtie index file: "%s"' % ifn)

def checkBowtie2Index(base, iGenomes=False):
    # Check existence of all the index files, large or small
    loc = iGenomesLoc if iGenomes else refLoc
    for ext in [ '.1.bt2', '.2.bt2', '.3.bt2', '.4.bt2', '.rev.1.bt2', '.rev.2.bt2']:
        ifn = '/'.join([base, loc['REF_BOWTIE2_INDEX'] + ext])
        if not (os.path.exists(ifn) or os.path.exists(ifn + 'l')):
            raise RuntimeError('No such Bowtie index file: "%s"' % ifn)

class RefConfigEmr(object):
    """ When in emr mode, this class's config method is the way to replace
        reference-related placeholders. """
    def __init__(self, emrLocalDir, iGenomes):
        self.emrLocalDir = os.path.abspath(emrLocalDir)
        self.iGenomes = iGenomes # this=True has never been tested
    
    def config(self, s):
        loc = iGenomesLoc if self.iGenomes else refLoc
        for k, v in loc.iteritems():
            tok = '%' + k.upper() + '%'
            if tok in s:
                if k.startswith('REF_INTRON_INDEX'):
                    s = s.replace(tok, 'intron/intron')
                else:
                    s = s.replace(tok, '/'.join([self.emrLocalDir, v]))
        return s

class RefConfigHadoop(object):
    """ When in hadoop mode, this class's config method is the way to replace
        reference-related placeholders. """
    def __init__(self, refDir, iGenomes, checkLocal):
        self.refDir = os.path.abspath(refDir)
        self.iGenomes = iGenomes
        self.checkLocal = checkLocal
    
    def config(self, s):
        loc = iGenomesLoc if self.iGenomes else refLoc
        for k, v in loc.iteritems():
            tok = '%' + k.upper() + '%'
            if tok in s:
                if self.checkLocal:
                    if k.startswith('REF_BOWTIE_INDEX'):
                        checkBowtieIndex(self.refDir, iGenomes=self.iGenomes)
                    if k.startswith('REF_BOWTIE2_INDEX'):
                        checkBowtie2Index(self.refDir, iGenomes=self.iGenomes)
                s = s.replace(tok, '/'.join([self.refDir, v]))
        return s

class RefConfigLocal(object):
    """ When in local mode, this class's config method is the way to replace
        reference-related placeholders. """
    def __init__(self, refDir, intermediateDir, outDir, iGenomes, checkLocal):
        self.refDir = os.path.abspath(refDir)
        self.intermediateDir = os.path.abspath(intermediateDir)
        self.outDir = os.path.abspath(outDir)
        self.iGenomes = iGenomes
        self.checkLocal = checkLocal
    
    def config(self, s):
        loc = iGenomesLoc if self.iGenomes else refLoc
        for k, v in loc.iteritems():
            tok = '%' + k.upper() + '%'
            if tok in s:
                if self.checkLocal:
                    if k.startswith('REF_BOWTIE_INDEX'):
                        checkBowtieIndex(self.refDir, iGenomes=self.iGenomes)
                    if k.startswith('REF_BOWTIE2_INDEX'):
                        checkBowtie2Index(self.refDir, iGenomes=self.iGenomes)
                if k.startswith('REF_INTRON_INDEX'):
                    s = s.replace(tok, '/'.join([self.outDir, v]))
                else:
                    s = s.replace(tok, '/'.join([self.refDir, v]))
        return s