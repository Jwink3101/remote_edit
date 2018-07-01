# Remote Editor

A tool to open remote documents and sync on edit. Call the function from a remote machine, and open it locally in an editor of your choosing.

Compatible with python 2 and 3

## Usage

On your *local* machine, run `python remote_editor.py` (or `pypy remote_editor.py`). In theory, you can run this in the background and/or in a subshell but you will have to either force close it or launch another instance (there is a fail-safe so two instances can't run at the same time).

On your remote machine, open the files with `call_remote_edit.sh` (which you should probably alias). Note that `call_remote_edit.sh` **can accept `stdin` (pipped input)** by making it into a temp file and opening that.

## Background

Many editors have an "Open with SFTP" option. And for those that don't, many SFTP clients have an "Open With" option. I do not know exactly how they work, but most have the same problem: If I am on the remote machine, I have to go to the local machine to open the remote document.

For a long time, I connected to linux from my mac. I used TextWrangler which could open SFTP via command line. So I would set up a remote edit script to call from my linux box to my mac, to open the file. But that (a) limited me to editors that could open a remote file over SFTP and (b) limited me to my mac.

When moving to a more linux to linux enviroment, I needed this built in and without external dependantcies (I work on segregated networks). Hence, `remote_editor` was born. It isn't perfect, but it does work well enough! 


## Requirements

This should work pretty easily. The only requirement is that each machine can ssh to the other. SSH keys going both ways is **STRONGLY** suggested to have SSH keys since every save and open is an ssh (or rsync over ssh) call.

While something like paramiko may improve performance by keeping an ssh tunnel open, I wanted this to work out of the box without any modules.

### SSH keys

The following can be used to generate SSH keys and send them to the other machine:

    $ cd
    $ ssh-keygen -t rsa
    $ # Enter a password (suggested) or to skip, hit Enter twice.
    $ cat ~/.ssh/id_rsa.pub | ssh user@other-system "mkdir -p ~/.ssh && cat >>  ~/.ssh/authorized_keys" 

## Config

There is very little configuration needed.

### Local Machine

On the local machine, all you need to do is somehow specify the editor. There are multiple ways to do it. Choose amongst the following (where they are in order of precedent)

Specify the text as `/path/to/editor {0:s}` since Python will use the `.format()` command. **NOTE the use of `\"` and `"`**

1. Specify the `REMOTE_EDITOR` in your bash environment. 
    * Example: `export REMOTE_EDITOR="/path/to/editor \"{0:s}\""`
2. Specify the string in your function start call
    * Example: `$ ./remote_editor.py "/path/to/editor \"{0:s}\""`
3. Do not specify. Will have to open it manually

There are also other options in the call which can modify the behavior

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


### Remote

The remote call script is also designed to work locally so you can always just specify the same command. However, you must specify a `LOCAL_EDITOR` environmental variable but **not** with the `{0:s}` format. Instead, just as a bash program. For example, `gedit` is a local GUI editor but it also tends to spew lots of warnings. I created the file:

`/path/to/gedit_wrapper.sh`:

    #!/usr/bin/env bash
    (nohup gedit "$@" >/dev/null 2>&1 &)

Then, in the `.bash_profile`, I specify:

    export LOCAL_EDITOR=/path/to/gedit_wrapper.sh

By default, it will assume the remote machine's username is the same as your local one. If not, set in your bash environment (or `.bashrc`/`.bash_profile`):

    export REMOTE_USER='username'

Otherwise, `REMOTE_USER` will default to `$USER`

As the comment suggest, modify that to the remote user name if they are not the same.

#### Manually adding files

Finally, if you can not SSH back to the loca machine from the remote, specify the global variable (or assign it to anything but `null`)

    export REMOTE_EDIT_MANUAL=1

which will then echo the command to add to the local machine without having to ssh to the local machine

**OR**

You can specify the edit command with `-m` as the first flag. For example, if you type *on the remote machine* (with `edit` aliased to `call_remote_edit`:

    $ edit -m file1

regardless of the `REMOTE_EDIT_MANUAL`, you will see:

    Manual Remote Edit. Enter the following:
        A: user@host /full/path/to/file1

for you to enter on the local machine

## Methodology

There are two parts to this code: `remote-editor.py` lives on the local machine and `call_remote_edit.sh` lives on the remote machine (usually aliased somehow).

First, `remote-editor.py` must be initiated on the local machine. This will clear the temp directory and start polling.

On the remote machine, when you call `call_remote_edit.sh`, it will, over SSH, write the file path to the local machine.

The local machine is actively polling the file written by `call_remote_edit.sh`. When it detects the queue file has changed, it will download the remote file (via rsync). It will begin to poll the file and anytime it is edited locally, it will push it back to the remote. If it is a new file, it will not pull it first.

If `call_remote_edit.sh` calls a file already locally, it will be pulled again. This can be used to update a file or if it has already been closed. (or use the `R` command on the local machine)

## Limitations

* Currently, this relies on polling the folders. In the future, it will make use of other APIs for updates.
* Future versions will use some mechanism to keep the connections open with something like paramiko
* Currently every update opens a new shell. This is probably not well used on remote or slow connections.
* If you modify the file remotely (say, with vim), it will not update the local copy unless you use `call_remote_edit.sh` on it again.
* If the instance is closed, you will have to call for remote editing on all files again. In the future, there may be a way to save and recover sessions (perhaps writing a JSON file).
* In theory, you could just specify a single editor string instead of a separate `REMOTE_EDITOR` (in Python string formatting) and `LOCAL_EDITOR`. However, the pattern for multiple files makes this easier.








