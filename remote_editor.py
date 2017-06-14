#!/usr/bin/env python

import os,shutil
import sys
from datetime import datetime
import time
from select import select
import getopt
import hashlib

if sys.version_info[0] == 2:
    input = raw_input
else:
    unicode = str

tmpdir = '/var/tmp/remote_edit/' # End in a /

openFiles = {}

starttime = unicode(time.time())
exittxt = """\
>> Options: (case insensitive)
    X   - break out (or CTRL + C)
    L   - List watched files
    A   - Manually add a file:
            Existing Ex `A: user@host /path/to/file`
            New File Ex `A: -user@host /path/to/file`
    R   - Referesh all files
=====================================================
"""


def _md5(input):
    m = hashlib.md5()
    m.update(unicode(input).encode('utf8'))
    return m.hexdigest()

def main(force=False):

    
    init(force=force)
    
    print(exittxt)
    
    try:
        while True:
            watch_loop()
            if pause_prompt():
                break
    except KeyboardInterrupt:
        pass
        
    print("Exiting. Clearing tmp files.")
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)

def init(force=False):
    """
    Started up running. Clear tmp folder and start file list
    """    
    if os.path.exists(tmpdir):
        if not force:
            print('WARNING: Files exist for `remote_editor`. Possible Explanations:')
            print('    * Previous run was exited forcibly (CTRL-X)')
            print('    * Another instance is running')
            print('Do you wish to continue (and force quite previous instance)? [Y/N]')
            response = input(' > ')
            if not response.lower().startswith('y'): 
                print('Exiting')
                sys.exit()
            print('Closing previous instance')
        shutil.rmtree(tmpdir)
    os.makedirs(tmpdir)
    
    # Write out the start time
    with open(tmpdir + 'start.txt','w') as F:
        F.write(starttime)

def watch_loop():
    """
    This is the main loop
    
        * Check for and processes new files
        * Look for changes
    """
    
    assert open(tmpdir + 'start.txt','r').read().strip() == starttime,"Another instance was started. Force-quitting this one"
            
    global openFiles
    
    anyMod = False
    
    if os.path.exists(tmpdir+'new'):
        anyMod = True
        # Read the file, delete it, then work on it
        with open(tmpdir+'new') as F:
            files = F.readlines()
        os.remove(tmpdir+'new')
        for file in files:
            new_file(file)
    
    # Loop over the files and look for mod times
    for fileDict in openFiles.values():
        # Get the current date
        moddate = modification_date(fileDict['fileName_full'])
        if moddate > fileDict['date']:
            anyMod = True
            fileDict['date'] = moddate # Update
            # push it
            cmd = 'rsync -az --no-p -e"ssh -q" "{fileName_full:s}" "{userhost:s}:{remotePath_s:s}"'.format(**fileDict)
            os.system(cmd)
            print(('Modified:{userhost:s}:{remotePath:s}'.format(**fileDict)))
    
    if anyMod:
        print(exittxt)

def pause_prompt():
    global timeout
    rlist, _, _ = select([sys.stdin], [], [], timeout)
    
    if rlist:
        s0 = sys.stdin.readline()
        s = s0.lower().expandtabs().strip()
        if len(s) == 0: return False
        if s[0] == 'x':
            return True
        elif s[0] == 'l':
            print("Watching:")
            for fileDict in openFiles.values():
                print('    {userhost:s}:{remotePath:s}\n      Local Path:{fileName_full:s}'.format(**fileDict))  
        elif s[0] == 'a':
            if s0[1] in [' ','\t']: # Also allow A [-]user@host /path/to/file
                s0 = s0.split(None,1)
            else:
                s0 = s0.split(':',1)
            if len(s0) == 1: 
                print('Must enter format `A: [-]user@host /path/to/file`')
                return False
            s0 = s0[-1].strip()
            new_file(s0)
            if s0.startswith('-'):
                print("WARNING: Remote file not pulled. Will overwrite on save")
        elif s[0] == 'r':
            refresh_all()
        else:
            print("Invalid Entry")
            print(exittxt)
    return False

def refresh_all():
    """ Refresh all files by acting as if they are just added """
    for file in openFiles.values():
        file = file['filestring']
        file = file.strip()
        if file.startswith('-'):
            file = file[1:]
        
        # Add a new file to pull it
        new_file(file,openFile=False)
    
    
def new_file(file,openFile=True):
    """
    Read and pull down new file
    """
    global openFiles
    
    # Format is 
    #   ${USER}"@"${HOSTNAME} " "${FILE}" 
    # or
    #   -${USER}"@"${HOSTNAME} " "${FILE}"
    # if it is a new file
    
    NEW = False
    if file.startswith('-'):
        NEW = True
        file = file[1:]
        
    try:
        userhost,filepath = file.strip().split(' ',1)
    except:
        print("Error with {:s}".format(file))
        return

    
    fileDict = {}
    fileDict['filestring'] = file
    fileDict['userhost'] = userhost
    
    # Make sure filepath is an absolute path. I.E. remove  ../ and ./
    filepath = os.path.normpath(filepath).strip()
    
    fileDict['remotePath'] = filepath
    fileDict['remotePath_s'] = fileDict['remotePath'].replace(' ','\ ')
    
    if name_only:
        fileDict['localDir'] = _md5(filepath)[:5] + '/'
    else:
        fileDict['localDir'] = os.path.join(_md5(filepath)[:3],
                            userhost.split('@',1)[-1],
                            os.path.split(filepath)[0][1:])
        
        
    fileDict['fileName'] = os.path.split(filepath)[1]
    
    # make the directory if it doesn't exist
    fileDict['localDir_full'] = os.path.join(tmpdir,fileDict['localDir'])
    if not os.path.exists(fileDict['localDir_full'] ):
        os.makedirs(fileDict['localDir_full'] )
    
    fileDict['fileName_full'] = os.path.join(fileDict['localDir_full'],fileDict['fileName'])
    fileDict['fileName_full_s'] = fileDict['fileName_full'].replace(' ','\ ')
    
    if NEW:
        with open(fileDict['fileName_full_s'],'w') as F: F.write('') # Empty file
    else:
        # Pull it. Build the rsync command and pull it
        cmd = 'rsync -az --no-p -e"ssh -q" "{userhost:s}:{remotePath_s:s}" "{fileName_full:s}"'.format(**fileDict)
        # print '----\n\n{:s}\n\n----'.format(cmd)
        os.system(cmd)
     
    fileDict['date'] = modification_date(fileDict['fileName_full'])
    
    # Add this. Will overwrite if it is already there or create new
    openFiles[fileDict['fileName_full']] = fileDict
    
    print('Added: {userhost:s}:{remotePath:s}'.format(**fileDict))
    print('   Local Path: {fileName_full:s}'.format(**fileDict))
    if NEW:
        print('   New file. Will upload (and overwrite) on save')
    
    if len(opencmd) == 0:
        print('     No local edit command specified. Open manually')
        return
    
    if openFile:
        os.system(opencmd.format(fileDict['fileName_full']))
    
    return
    
def modification_date(filename):
    """ from http://stackoverflow.com/a/1526089 """
    t = os.path.getmtime(filename)
    return datetime.fromtimestamp(t) 


usage = """
remote_editor.py -- Tool for remotely managing files.

Usage:
    run `remote_editor.py` locally. Call with `call_remote_edit.sh` on remote
    system when logged in via SSH
    
    python remote_editor.py [OPTIONS] [EDITOR]
    
Options: ( `=` requires input, [default])
    -f,--force
        Force starting this instance. Do not prompt if it thinks another is
        running. Will close the other
        
    -h      
        Display this help

    -s,--short
        Set the folder names to be shorter. Otherwise, it will replicate
        the full path
    
    -t=,--polling=
        [0.333] Specify the time between polling for an updated file

EDITOR String: (see `readme.md` for more detail)
    
    You should specify the editor to use.
    
    Specify the text as `/path/to/editor {0:s}` since Python will use 
    the `.format()` command.
    
    Choices are (in order of precedence)

        1. Specify the `REMOTE_EDITOR` in your bash environment. 
            * Example: `export REMOTE_EDITOR="/path/to/editor \\"{0:s}\\""`
        2. Specify the string in your function start call
            * Example: `$ python remote_editor.py "/path/to/editor {0:s}"`
        3. Do not specify. Will have to open it manually
"""

if __name__=='__main__':
    #print(sys.version)
    os.system('echo -ne "\033]0;{name}\007"'.format(name='remote edit watcher'))
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "fhst:", ["force","help","short","polling="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print('{}'.format(err)) # will print something like "option -a not recognized"
        print("\n Printing Help:\n")
        print(usage)
        sys.exit(2)
  
    print("Running remote_editor.")
    print("Restarting will clear all open files")
    
    ## Process the options
    # Defaults
    force = False
    timeout = 0.3333
    name_only = False
    
    for  o,a in opts:
        if o in ['-f','--force']:
            force = True
        if o in ["-h","--help"]:
            print(usage)
            sys.exit()
        if o in ['-s','--short']:
            name_only = True        
        if o in ['-t','--polling']:
            timeout = float(a)
    
    # Try to get the opencmd
    global opencmd
    opencmd = ''
    if 'REMOTE_EDITOR' in list(os.environ.keys()) and len(os.environ['REMOTE_EDITOR'])>0:
        opencmd = os.environ['REMOTE_EDITOR']
        print("Remote Edit set in environmental variable")
        print("   " + opencmd)
    elif len(args)>0:
        opencmd = args[0]
        print("Remote Edit set function call")
        print("   " + opencmd)        
    
    else:
        print("No editor set")
    
    main(force=force)



















