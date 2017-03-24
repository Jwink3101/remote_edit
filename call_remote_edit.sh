#!/usr/bin/env bash


# First see if you're remote. If not use local editor
# Adapted from #2
SESSION_TYPE="direct"
if [ -n "$SSH_CLIENT" ] || [ -n "$SSH_TTY" ]; then
    SESSION_TYPE="ssh"
    # many other tests omitted
else
    case $(ps -o comm= -p $PPID) in
        sshd|*/sshd) SESSION_TYPE="ssh";;
    esac
fi

# See if input is being pipped in. If so, store it in a temp file
if [ ! -t 0 ]; then
    rand=$(echo $RANDOM | tr '[0-9]' '[a-zA-Z]')
    
    A="/tmp/$rand/piped_stdin"
    
    rm $a > /dev/null 2>&1 
    mkdir -p "/tmp/$rand"
    
    IFS=''
    while read -r line ; do
        echo $line >> $A
    done
    set $A # Sets the positional location
fi


if [ $SESSION_TYPE == 'direct' ]; then
#     for j in "$@"; do
#         # Set the remote function as an environmental variable, otherwise, default
#         # to the $EDITOR
#         if [ ! -z "$LOCAL_EDITOR" ]; then
#             eval "$LOCAL_EDITOR $j"
#         else
#             eval "$EDITOR $j"
#         fi
#     done
    if [ ! -z "$LOCAL_EDITOR" ]; then
        eval "$LOCAL_EDITOR $@"
    else
        eval "$EDITOR $@"
    fi
else
    HOSTNAME=`hostname`
    USER=`whoami`
    TTY=$(echo $SSH_TTY | sed 's@/dev/@@g')
    
    if [ -z $REMOTE_USER ]; then
        REMOTE_USER=$USER
    fi
    
    manualmode='' # default, unset
    if [ "$1" == '-m' ]; then
        manualmode='set' # now it exists on a `! -z` flag
        shift
    fi

    if [ ! -z $REMOTE_EDIT_MANUAL ] || [ ! -z $manualmode ]; then
        echo "Manual Remote Edit. Enter the following:"
    fi

    # It seems as though "$@" already has the wild-cards expanded if they exist but keep this here anyway
    for j in "$@";do # loop through files
        F=$(ls "$j" 2> /dev/null | wc -l) #ref 1, returns 1 if the file exists
    
    
        txt=""
        if [ "$F" == "0" ]; then
            touch "$j" # Create the file, then delete it. Will be recreated if saves remotely
        fi

        FILE=$(ls "$j")

        if [[ "$FILE" != /* ]]; then
            FILE="$PWD/$FILE"
        fi
    
        if [ "$F" == "0" ]; then
            rm "$j"
            txt='-'
        fi
    
        exttxt=""
        if [ -L "$FILE" ]; then
            FILE0=$FILE
            FILE=$(ls -l "$FILE" | sed -e 's/.* -> //')
            FILE=$(echo "$(cd "$(dirname "$FILE")"; pwd)/$(basename "$FILE")") # Expand relative paths -- [3]
            echo "File $FILE0 --> $FILE"
            exttxt="  "
        fi

        txt="$txt$USER@$HOSTNAME ${FILE}" 	
        if [ ! -z $REMOTE_EDIT_MANUAL ] || [ ! -z $manualmode ]; then
            echo "    A: $txt"
        else
            REMOTE=$(who|grep "\b$TTY\b" | cut -d "(" -f2 | cut -d ")" -f1)
            echo "${exttxt}Remote Edit: $txt"
            ssh ${REMOTE_USER}@${REMOTE}  "echo $txt >> /var/tmp/remote_edit/new" 2>/dev/null || echo "  ERROR: Is this a folder? Is remote_editor running?"
        fi
        
    done
fi


# ref:
#1: http://stackoverflow.com/questions/6363441/check-if-a-file-exists-with-wildcard-in-shell-script
#2: http://unix.stackexchange.com/a/9607
#3: http://stackoverflow.com/a/3915420/3633154
