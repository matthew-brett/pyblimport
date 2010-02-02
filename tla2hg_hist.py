#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
   Convert a repository to mercurial (hg).

   http://www.linux-france.org/~dmentre/misc/tla-to-hg-hist.py
   
   This runs with baz 1.1.1  and also with tla 1.3-1 - if you do changes,
   maybe either try to avoid stuff requiring latest versions (it means
   much trouble for people trying to convert).

   TODO:
    * test reading tla multiline comments (had no testcase)
    * commit timestamps are UTC now, maybe use localtime?

   @license: BSD ???
   @copyright: 2005 Sam Tardieu
   @copyright: 2005 Ollivier Robert
   @copyright: 2005 Thomas Waldmann (rewrite, optimize)
   @copyright: 2006 David MENTRE (full history, tested with tla 1.3)
"""
import os, sys, time
import subprocess


# it works with either one:
archcmd = "tla"
#archcmd = "baz"


def shcall(cmd, check=True):
    if check:
        return subprocess.check_call(cmd, shell=True)
    return subprocess.call(cmd, shell=True)

    
def shrun(cmd, ret_error=False, ret_code=False):
    proc = subprocess.Popen(cmd,
                 stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE,
                 shell=True)
    (out, err) = proc.communicate()
    if not (ret_error or ret_code):
        return out
    ret = [out]
    if ret_error:
        ret.append(err)
    if ret_code:
        ret.append(proc.returncode)
    return ret


def get_revisions(archive, remove=True, from_existing=False):
    """get revision list of archive"""
    if not from_existing:
        shcall("%s get %s tmp-archive" % (archcmd, archive))
    revlist = shrun("cd tmp-archive && %s ancestry-graph --reverse"
                    % archcmd)
    if remove==True:
        os.removedirs('tmp-archive')
    # because of the ancestry graph, we get full revision ids
    revlist = [r for r in revlist.split('\n') if r]
    version_list = []
    for r in revlist:
        fullrev = r.split('\t')[0].strip()
        version_list.append(fullrev)
    return version_list


def read_summary(fullrev):
    author = ""
    date = ""
    summary = []
    skip_line = False
    log_lines = shrun("%s cat-archive-log %s" % (archcmd, fullrev))
    log_lines = [L for L in log_lines.split('\n') if L]
    for l in log_lines:
        if len(summary) == 0:
            if l.startswith("Creator: "):
                author = l[9:].strip()
            elif l.startswith("Standard-date: "): # this is UTC
                datestr = l[15:].strip()
                t = time.mktime(time.strptime(datestr, "%Y-%m-%d %H:%M:%S %Z"))
                date = "%d 0" % int(t)
            elif l.startswith("Summary: "):
                summary = [l[9:].strip()]
                skip_line = True
        elif skip_line: # skip one line
            skip_line = False
        else: # we have begun reading the summary, continues until eof...
            stripped = l.rstrip()
            if l and stripped != summary[0]:
                summary.append(stripped)
    summary.extend(["", "imported from: %s" % fullrev])
    return summary, author, date


def commit_log(fullrev, mercurial_dir):
    summary, author, date = read_summary(fullrev)
    try:
        fd = open('tmp-msg', 'w')
        fd.write('\n'.join(summary) + '\n')
        fd.close()
        shcall("cd %s && hg commit "
               "--addremove -l ../tmp-msg --date '%s' --user '%s'"
               % (mercurial_dir, date, author))
    finally:
        os.remove('tmp-msg')


def make_initial_revision(fullrev, mercurial_dir):
    """make initial hg repository"""
    sys.stdout.write(">>> '%s'\n" % fullrev)
    shcall("%s get %s %s" % (archcmd, fullrev, mercurial_dir))
    hgi = open("%s/.hgignore" % mercurial_dir, "w")
    hgi.write("""\
.arch-ids/.*
\{arch\}/.*
""")
    hgi.close()
    shcall("cd %s && hg init" % mercurial_dir)
    commit_log(fullrev, mercurial_dir)


def import_revision(archive, fullrev, mercurial_dir):
    """import a single arch revision into an hg repo"""
    sys.stdout.write(">>> '%s'\n" % fullrev)
    shcall("cd %s && %s replay %s" % (mercurial_dir, archcmd, fullrev))
    commit_log(fullrev, mercurial_dir)


def tla_to_hg(archive, mercurial_dir):
    if not os.path.exists(mercurial_dir):
        os.mkdir(mercurial_dir)
    version_list = get_revisions(archive)
    make_initial_revision(version_list[0], mercurial_dir)
    for fullrev in version_list[1:]:
        import_revision(archive, fullrev, mercurial_dir)


if __name__ == '__main__':
    try:
        cmd, archive, mercurial_dir = sys.argv[:3]
    except IndexError:
        sys.stdout.write("""\
    Usage: arch-to-hg.py archive target_dir

    archive: the tla/baz archive you are converting from
    target_dir: where to put conversion results in hg format, must be some
                directory in the current directory, like "outputdir".
    """)
    tla_to_hg(archive, mercurial_dir)
    

