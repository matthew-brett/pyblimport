#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
   Convert a repository to mercurial (hg) or git

   David Mentre version found at:
   
   http://www.linux-france.org/~dmentre/misc/tla-to-hg-hist.py
   
   This runs with baz 1.1.1 and also with tla 1.3.5 - if you do changes,
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
   @copyright: 2010 Matthew Brett (added git conversion, refactored)
"""
import os, sys, time
import subprocess
import shutil

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


class Repo(object):
    def __init__(self, repo_path):
        self.repo_path = repo_path

    def import_revision(self, fullrev):
        """import a single arch revision into repo"""
        sys.stdout.write(">>> '%s'\n" % fullrev)
        shcall("%s replay --dir %s %s" % (archcmd,
                                          self.repo_path,
                                          fullrev))
        self.commit_log(fullrev)

    def commit_log(self, fullrev):
        summary, author, date = read_summary(fullrev)
        msg_fname = os.path.abspath('tmp-msg')
        fd = open(msg_fname, 'wt')
        fd.write('\n'.join(summary) + '\n')
        fd.close()
        self.do_commit(msg_fname, date, author)
        os.remove(msg_fname)

    def make_initial_revision(self, fullrev):
        """make initial repository"""
        sys.stdout.write(">>> '%s'\n" % fullrev)
        shcall("%s get %s %s" % (archcmd, fullrev, self.repo_path))
        self.init_repo()
        self.commit_log(fullrev)

    def import_branch_version(self, branch_version):
        version_list = get_revisions(branch_version)
        self.make_initial_revision(version_list[0])
        for fullrev in version_list[1:]:
            self.import_revision(fullrev)


class HgRepo(Repo):
    def init_repo(self):
        hgi = open("%s/.hgignore" % self.repo_path, "w")
        hgi.write("""\
.arch-ids/.*
.arch-inventory
\{arch\}/.*
""")
        hgi.close()
        shcall("cd %s && hg init" % self.repo_path)
        
    def do_commit(self, msg_fname, date, author):
        shcall("cd %s && hg commit "
               "--addremove -l %s --date '%s' --user '%s'"
               % (self.repo_path, msg_fname, date, author))
        

class GitRepo(Repo):
    def init_repo(self):
        giti = open("%s/.gitignore" % self.repo_path, "w")
        giti.write("""\
.arch-ids/
.arch-inventory
\{arch\}/
""")
        giti.close()
        shcall('cd %s && git init' % self.repo_path)

    def do_commit(self, msg_fname, date, author):
        cmd = ("cd %s && "
               "git add . && " # git version of --addremove in hg
               "git ls-files --deleted | xargs git rm && " 
               "GIT_AUTHOR_DATE='%s' " # note no &&
               "git commit --file=%s --author='%s'" % 
               (self.repo_path, date, msg_fname, author))
        res, err, code  = shrun(cmd, ret_error=True, ret_code=True)
        if code != 0:
            if 'nothing to commit' not in res:
                raise RuntimeError("""
%s failed with:
code: %d
stdout: %s
stderr: %s
"""  % (cmd, code, res, err))

    
def get_revisions(branch_version):
    """get revision list of branch_version"""
    shcall("%s get %s tmp-archive" % (archcmd, branch_version))
    revlist = shrun("cd tmp-archive && %s ancestry-graph --reverse"
                    % archcmd)
    shutil.rmtree('tmp-archive', ignore_errors=True)
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
    for l in os.popen("%s cat-archive-log %s" % (archcmd, fullrev)):
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
    summary = [s.decode('ascii', 'ignore') for s in summary]
    return summary, author, date


def convert_version(branch_version, repo_path, vcs_type='hg'):
    repo = STR2REPO[vcs_type](repo_path)
    repo.import_branch_version(branch_version)

    
STR2REPO = {'hg': HgRepo, 'git': GitRepo}


if __name__ == '__main__':
    try:
        cmd, branch_version, repo_path = sys.argv[:3]
    except IndexError:
        sys.stdout.write("""\
    Usage: %s branch-version repo-path [vcs-type]

    branch-version: the tla/baz branch version you are converting from

    repo-path: where to put conversion results in repository-specific
               format

    vcs-type: one of 'hg' or 'git' (default is 'hg')

    e.g. ``%s pyblio--stable--1.2 pyblio-1.2 git``

    Note that you will need to register all archives with relevant
    history beforehand, using 'tla' or 'baz' ``register-archive``, and
    the archive with the relevant branch-version will need to be your
    default archive (``tla|baz my-default-archive <archive-name>``). 
    You will need a defined user in your environment for the version
    control system you use (e.g. via ``.hgrc`` or ``.gitconfig``).
    """) % (cmd, cmd)
    try:
        vcs_type = sys.argv[3]
    except IndexError:
        vcs_type = 'hg'
    convert_version(branch_version, repo_path, vcs_type)
    

