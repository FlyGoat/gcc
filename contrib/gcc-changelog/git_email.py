#!/usr/bin/env python3

# Copyright (C) 2020-2024 Free Software Foundation, Inc.
#
# This file is part of GCC.
#
# GCC is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 3, or (at your option) any later
# version.
#
# GCC is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with GCC; see the file COPYING3.  If not see
# <http://www.gnu.org/licenses/>.

import os
import re
import sys
import argparse
import tempfile
from itertools import takewhile

from dateutil.parser import parse

from git_commit import GitCommit, GitInfo, decode_path

from unidiff import PatchSet, PatchedFile

DATE_PREFIX = 'Date: '
FROM_PREFIX = 'From: '
SUBJECT_PREFIX = 'Subject: '
subject_patch_regex = re.compile(r'^\[PATCH( \d+/\d+)?\] ')
unidiff_supports_renaming = hasattr(PatchedFile(), 'is_rename')


class GitEmail(GitCommit):
    def __init__(self, filename):
        self.filename = filename
        date = None
        author = None
        subject = ''

        subject_last = False
        with open(self.filename, newline='\n') as f:
            data = f.read()
            diff = PatchSet(data)
            lines = data.splitlines()
        lines = list(takewhile(lambda line: line != '---', lines))
        for line in lines:
            if line.startswith(DATE_PREFIX):
                date = parse(line[len(DATE_PREFIX):])
            elif line.startswith(FROM_PREFIX):
                author = GitCommit.format_git_author(line[len(FROM_PREFIX):])
            elif line.startswith(SUBJECT_PREFIX):
                subject = line[len(SUBJECT_PREFIX):]
                subject_last = True
            elif subject_last and line.startswith(' '):
                subject += line
            elif line == '':
                break
            else:
                subject_last = False

        if subject:
            subject = subject_patch_regex.sub('', subject)
        header = list(takewhile(lambda line: line != '', lines))
        # Note: commit message consists of email subject, empty line, email body
        message = [subject] + lines[len(header):]

        modified_files = []
        for f in diff:
            # Strip "a/" and "b/" prefixes
            source = decode_path(f.source_file)[2:]
            target = decode_path(f.target_file)[2:]

            if f.is_added_file:
                t = 'A'
            elif f.is_removed_file:
                t = 'D'
            elif unidiff_supports_renaming and f.is_rename:
                # Consider that renamed files are two operations: the deletion
                # of the original name and the addition of the new one.
                modified_files.append((source, 'D'))
                t = 'A'
            else:
                t = 'M'
            modified_files.append((target if t != 'D' else source, t))
        git_info = GitInfo(None, date, author, message, modified_files)
        super().__init__(git_info, commit_to_info_hook=None)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=('Check git ChangeLog format of a patch.\n'
                     'Patch files must be in \'git format-patch\' format.'),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'files', 
        nargs='*', 
        help=('Patch files to process.\n'
              'Use "-" to read from stdin.\n'
              'If none provided, processes all files in ./patches directory')
    )
    parser.add_argument('-p', '--print-changelog', action='store_true',
                        help='Print final changelog entires')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Don\'t print "OK" and summary messages')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Print verbose information')
    args = parser.parse_args()

    batch_mode = False
    tmp = None

    if not args.files:
        # Process all files in patches directory
        allfiles = []
        for root, _dirs, files in os.walk('patches'):
            for f in files:
                full = os.path.join(root, f)
                allfiles.append(full)
        
        files_to_process = sorted(allfiles)
        batch_mode = True
    else:
        # Handle filelist or stdin
        if args.files[0] == '-':
            tmp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
            tmp.write(sys.stdin.read())
            tmp.flush()
            tmp.close()
            files_to_process = [tmp.name]
        else:
            files_to_process = args.files

    success = 0
    fail = 0
    total = len(files_to_process)
    batch_mode = batch_mode or total > 1

    if total == 0:
        print('No files to process', file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    for full in files_to_process:
        email = GitEmail(full)

        res = 'OK' if email.success else 'FAILED'
        have_message = not email.success or (email.warnings and args.verbose)
        if not args.quiet or have_message:
            filename = '-' if tmp else email.filename
            print('Checking %s: %s' % (filename, res))

        if email.success:
            success += 1
            if args.verbose:
                for warning in email.warnings:
                    print('WARN: %s' % warning)
            if args.print_changelog:
                    email.print_output()
        else:
            fail += 1
            if not email.info.lines:
                print('ERR: patch contains no parsed lines')
                continue
            if args.verbose:
                for warning in email.warnings:
                    print('WARN: %s' % warning)
            for error in email.errors:
                print('ERR: %s' % error)
        
        if have_message or batch_mode:
            print()

    if batch_mode and not args.quiet:
        print('Successfully parsed: %d/%d' % (success, total))

    if tmp:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    sys.exit(fail > 0)
