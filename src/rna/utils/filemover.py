"""
filemover.py
Part of Dooplicity framework

Utilities for moving files around among local, hdfs, s3, http and ftp
filesystems.
"""

import os
import sys
import subprocess
import time
import threading
import pipes
import re

def add_args(parser):
    """ Sets up arguments related to moving files around. """
    parser.add_argument(\
        '--s3cfg', metavar='STR', type=str, required=False,
        help='s3cmd configuration file to use (only relevant if some ' \
             'output is being pushed to S3)')
    parser.add_argument(\
        '--acl-public', action='store_const', const=True, default=False,
        help='Make files uploaded to S3 publicly-readable (only relevant if '
             'some output is being pushed to S3)')

class CommandThread(threading.Thread):
    """ Runs a command on a separate thread. """
    def __init__(self, command_list):
        super(CommandThread, self).__init__()
        self.command_list = command_list
        self.command = ' '.join(command_list)
        self.process_return, self.process = None, None
        self.content_disposition_filename = None
    def run(self):
        self.process \
            = subprocess.Popen(self.command,
                                    bufsize=-1,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    shell=True,
                                    executable='/bin/bash')
        # This is just for getting Content-Disposition from cURL
        for line in self.process.stdout:
            if re.match('content-disposition:', line[1:].lstrip(), re.I):
                match = re.search(r'filename=(.+)', line, re.I)
                if match and match.group(1):
                    self.content_disposition_filename = (
                                match.group(1).strip().strip('"')
                            )
                    print >>sys.stderr, (
                                'Filename {} from content-disposition header '
                                'found.'
                            ).format(self.content_disposition_filename)
            else:
                print >>sys.stderr, line,
        self.process_return = self.process.wait()

class FileMover(object):
    """ Responsible for details on how to move files to and from URLs. """
    
    def __init__(self, args=None, s3cmd_exe='s3cmd', s3cred=None,
                    s3public=False):
        try:
            self.s3cred = args.s3cfg
        except AttributeError:
            self.s3cred = s3cred
        try:
            self.s3public = args.acl_public
        except AttributeError:
            self.s3public = s3public
        self.s3cmd_exe = s3cmd_exe
    
    def put(self, filename, url):
        """ Uploads a local file to a URL.

            filename: path to file to upload
            url: URL to which file should be uploaded. Can be directory name
                + '/' or actual file.

            No return value.
        """
        assert os.path.exists(filename)
        if url.is_s3:
            command_list = [self.s3cmd_exe]
            if self.s3cred is not None:
                command_list.append('-c')
                command_list.append(self.s3cred)
            command_list.append('sync')
            if self.s3public:
                command_list.append("--acl-public")
            command_list.extend(
                    [filename, url.to_nonnative_url(),
                        '--server-side-encryption',
                        '--stop-on-error']
                )
        elif url.is_curlable:
            raise RuntimeError('Can\'t upload to http/ftp URLs.')
        elif url.is_local or url.is_nfs:
            try:
                os.makedirs(os.path.dirname(url.to_url()))
            except OSError:
                # Directory exists
                pass
            command_list = ['cp', filename, url.to_url()]
        else:
            assert url.to_url().startswith('hdfs:'), (
                    'Cannot identify filesystem for "{}".'
                ).format(url.to_url())
            command_list = ['/opt/hadoop/bin/hdfs', 'dfs', '-mkdir', '-p',
                                    os.path.dirname(url.to_url())]
            command = ' '.join(command_list)
            print >>sys.stderr, (
                    'Creating directory with command "{}".'
                ).format(' '.join(command_list))
            subprocess.Popen(command,
                stdout=sys.stderr, shell=True,
                executable='/bin/bash').wait()
            command_list = ['/opt/hadoop/bin/hdfs', 'dfs', '-put', filename, url.to_url()]
        command = ' '.join(command_list)
        print >>sys.stderr, 'Uploading with command "{}"....'.format(
                command
            )
        exit_level = subprocess.Popen(
                command, stdout=sys.stderr,
                shell=True, executable='/bin/bash').wait()
        if exit_level > 0:
            raise RuntimeError('Non-zero exitlevel %d from push command "%s".'
                               % (exit_level, command))

    def exists(self, url):
        if url.is_local:
            return os.path.exists(url.to_url())
        elif url.is_curlable:
            curl_command = ' '.join(['curl', '--head', url.to_url()])
            curl_process = subprocess.Popen(curl_command,
                                bufsize=-1, stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                shell=True, executable='/bin/bash')
            curl_err = curl_process.stderr.read()
            curl_process.wait()
            if 'resolve host' in curl_err:
                return False
            return True
        elif url.is_s3:
            command_list = [self.s3cmd_exe]
            if self.s3cred is not None:
                command_list.append('-c')
                command_list.append(self.s3cred)
            command_list.extend(['ls', url])
            s3cmd_process = subprocess.Popen(command_list, 
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE)
            url_string = url.to_url()
            for line in s3cmd_process.stdout:
                if (url_string + '\n') in line or (url_string + '/\n') in line:
                    return True
            s3cmd_process.wait()
            return False
        else:
            return False
    
    def get(self, url, dest="."):
        """ Get a file to local directory.

            url: Remote location of file.
            dest: Local destination of file.

            No return value.
        """
        if url.is_s3:
            command_list = ['s3cmd']
            if self.s3cred is not None:
                command_list.append('-c')
                command_list.append(self.s3cred)
            filename = os.path.join(dest, url.to_url().rpartition('/')[2])
            command_list.extend(
                    ['get', url.to_nonnative_url(), '-', '--force',
                        '>' + pipes.quote(filename)]
                )
            command = ' '.join(command_list)
            tries = 0
            while tries < 5:
                break_outer_loop = False
                s3cmd_process \
                    = subprocess.Popen(command, stdout=sys.stderr,
                                            shell=True, executable='/bin/bash')
                time.sleep(1)
                last_print_time = time.time()
                try:
                    last_size = os.path.getsize(filename)
                except OSError:
                    last_size = 0
                while s3cmd_process.poll() is None:
                    now_time = time.time()
                    if now_time - last_print_time > 120:
                        print >>sys.stderr, '\nreporter:status:alive'
                        sys.stderr.flush()
                        try:
                            new_size = os.path.getsize(filename)
                        except OSError:
                            new_size = 0
                        if new_size == last_size:
                            # Download stalled
                            break_outer_loop = True
                            break
                        else:
                            last_size = new_size
                        last_print_time = now_time
                        time.sleep(1)
                if break_outer_loop:
                    tries += 1
                    print >>sys.stderr, 'Download stalled on try %d.' % tries
                    s3cmd_process.kill()
                    try:
                        os.remove(filename)
                    except OSError:
                        pass
                    time.sleep(2)
                    continue
                if s3cmd_process.poll() > 0:
                    raise RuntimeError('Non-zero exitlevel %d from s3cmd '
                                       'get command "%s"' % (
                                                        s3cmd_process.poll(),
                                                        command)
                                                    )
                break
            if tries > 5:
                raise RuntimeError('Could not download file from S3 '
                                   'within 5 tries.')
        elif url.is_curlable:
            oldp = os.getcwd()
            os.chdir(dest)
            command_list = [
                    'curl', '-s', '-O', '-J', '-v', '-L',
                    '--connect-timeout', '600'
                ]
            command_list.append(url.to_url())
            command = ' '.join(command_list)
            filename = os.path.join(dest, url.to_url().rpartition('/')[2])
            tries = 0
            while tries < 5:
                break_outer_loop = False
                curl_thread = CommandThread(command_list)
                curl_thread.start()
                last_print_time = time.time()
                try:
                    last_size = os.path.getsize(filename)
                except OSError:
                    if curl_thread.content_disposition_filename:
                        print >>sys.stderr, (
                                'Switching to filename {} from '
                                'content-disposition header.'
                            ).format(curl_thread.content_disposition_filename)
                        filename = curl_thread.content_disposition_filename
                        try:
                            last_size = os.path.getsize(filename)
                        except OSError:
                            last_size = 0
                    else:
                        last_size = 0
                while curl_thread.is_alive():
                    now_time = time.time()
                    if now_time - last_print_time > 160:
                        print >>sys.stderr, '\nreporter:status:alive'
                        sys.stderr.flush()
                        try:
                            new_size = os.path.getsize(filename)
                        except OSError:
                            if (curl_thread.content_disposition_filename
                                    and filename !=
                                    curl_thread.content_disposition_filename):
                                print >>sys.stderr, (
                                    'Switching to filename {} from '
                                    'content-disposition header.'
                                ).format(
                                    curl_thread.content_disposition_filename
                                )
                                filename = \
                                    curl_thread.content_disposition_filename
                                try:
                                    new_size = os.path.getsize(filename)
                                except OSError:
                                    new_size = 0
                            else:
                                new_size = 0
                        if new_size == last_size:
                            # Download stalled
                            break_outer_loop = True
                            break
                        else:
                            last_size = new_size
                        last_print_time = now_time
                        time.sleep(1)
                    time.sleep(1)
                if break_outer_loop:
                    tries += 1
                    print >>sys.stderr, 'Download stalled on try %d.' % tries
                    try:
                        curl_thread.process.kill()
                    except AttributeError:
                        pass
                    try:
                        os.remove(filename)
                    except OSError:
                        pass
                    time.sleep(2)
                    continue
                if curl_thread.process_return > 89 \
                    or curl_thread.process_return == 56:
                    '''If the exit code is greater than the highest-documented
                    curl exit code, there was a timeout.'''
                    print >>sys.stderr, 'Too many simultaneous connections; ' \
                                        'restarting in 10 s.'
                    time.sleep(5)
                else:
                    break
            os.chdir(oldp)
            if curl_thread.process_return > 0:
                raise RuntimeError(('Nonzero exitlevel %d from curl command '
                                    '"%s"') 
                                        % (curl_thread.process_return,
                                            command))
        elif url.is_local:
            command_list = ['cp', url.to_url(), dest]
            exit_level \
                = subprocess.Popen(command_list, stdout=sys.stderr).wait()
            if exit_level > 0:
                raise RuntimeError('Nonzero exitlevel %d from cp '
                                   'command "%s"' % (exit_level, 
                                        ''.join(command_list)))
        else:
            command_list = [
                    "/opt/hadoop/bin/hdfs", "dfs", "-get",
                    url.to_url(),
                    dest
                ]
            command = ''.join(command_list)
            print >>sys.stderr, 'Downloading with command "{}"....'.format(
                command
            )
            exit_level \
                = subprocess.Popen(command_list, stdout=sys.stderr).wait()
            if exit_level > 0:
                raise RuntimeError('Nonzero exitlevel %d from get '
                                   'command "%s"' % (exit_level,
                                        command))
