#!/usr/bin/env python

import os
from os.path import join as pjoin, abspath, isdir, isfile, dirname
import sys
import subprocess
import shutil

import tla2hg_hist as tla
reload(tla)
from tla2hg_hist import  shcall, shrun


arch_cmd = 'tla'
archives = ('2007', '2006', '2005', 'public')
# from tla abrowse ftp://arch.pybliographer.org/archives/2007
'''
gobry@pybliographer.org--2007
  pyblio
    pyblio--devel
      pyblio--devel--1.3
        base-0 .. patch-23

    pyblio--legacy
      pyblio--legacy--1.3
        base-0 .. version-0

    pyblio--stable
      pyblio--stable--1.2
        base-0 .. patch-30

  pyblio-core
    pyblio-core--devel
      pyblio-core--devel--1.3
        base-0 .. patch-29

  python-bibtex
    python-bibtex--devel
      python-bibtex--devel--1.3
        base-0

    python-bibtex--stable
      python-bibtex--stable--1.2
        base-0
'''
projects = (
    ('pyblio--devel--1.3', 'pyblio-devel-1.3'),
    )

# Set our own archive command to module global
tla.archcmd = arch_cmd


def pyblio_archive_map(archives, base_location, source=True):
    if source:
        suffix = '-SOURCE'
    else:
        suffix = ''
    archive_map = {}
    for archive in archives:
        location = os.path.join(base_location, archive)
        name = 'gobry@pybliographer.org--%s%s' % (archive, suffix)
        archive_map[archive] = (name, location)
    return archive_map


def register_archives(archive_map, remove=False):
    if remove:
        flag = '-d'
    else:
        flag = ''
    for code, name_location in archive_map.items():
        name, location = name_location
        shcall('%s register-archive %s %s %s' % (
                arch_cmd, flag, name, location),
               check=False)


def clear_archives():
    arch_names = shrun('tla archives --names').split('\n')
    for name in [n for n in arch_names if n]:
        shcall('tla register-archive -d ' + name)


def mirror_archives(archive_map, archive_dir, source_suffix='-SOURCE'):
    # http://www.enyo.de/fw/software/arch/get.html#6
    archive_dir = os.path.abspath(archive_dir)
    new_map = {}
    for code, name_location in archive_map.items():
        name, location = name_location
        new_name = name
        if new_name.endswith(source_suffix):
            if len(source_suffix):
                new_name = new_name[:-len(source_suffix)]
        new_location = os.path.join(archive_dir, code)
        shcall('tla make-archive '
               '--mirror-from %s %s' % (name, new_location),
               check=False)
        shcall('tla archive-mirror %s' % new_name, check=False)
        new_map[code] = (new_name, new_location)
    return new_map


def set_default_archive(archive_name):
    shcall('%s my-default-archive %s'
           % (arch_cmd, archive_name))


def import_projects(projects):
    for arch_proj, hg_proj in projects:
        shutil.rmtree(hg_proj, ignore_errors=True)
        tla.tla_to_hg(arch_proj, hg_proj)


if __name__ == '__main__':
    # don't forget to set an hg username
    clear_archives()
    shcall('tla my-id "Matthew Brett <matthew.brett@gmail.com>"')
    #archive_dir = os.path.abspath('archives')
    #amap = pyblio_archive_map(archives,
    #                          'ftp://arch.pybliographer.org/archives',
    #                          source=False)
    # currently working with fuse mount of ftp
    amap = pyblio_archive_map(archives,
                              '/home/matthew/dev_trees/pybliographer/archives',
                              source=False)
    register_archives(amap)
    #mirror_archives(amap, archive_dir)
    #amap = pyblio_archive_map(archives,
    #                          archive_dir,
    #                          source=False)
    #register_archives(amap, remove=True)
    set_default_archive(amap['2007'][0])
    import_projects(projects)
    #revs = tla.get_revisions('pyblio--devel--1.3'))
    
