#!/usr/bin/env python
"""
tempdel.py
Part of Rail-RNA

For deleting temporary directories on exit from Python script.
"""
import shutil

def add_args(parser):
    parser.add_argument(\
        '--scratch', type=str, required=False,
        default=None,
        help='Path to scratch directory for storing temporary files. If left '
             'unspecified, it\'s taken to be a securely created temporary '
             'directory.')

def remove_temporary_directories(temp_dir_paths):
    """ Deletes temporary directory.

        temp_dir_paths: iterable of paths of temporary directories

        No return value.
    """
    for temp_dir_path in temp_dir_paths:
        try:
            shutil.rmtree(temp_dir_path,
                            ignore_errors=True)
        except Exception as e:
            # Don't know what's up, but forge on
            pass
