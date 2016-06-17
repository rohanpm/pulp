#!/bin/sh
# Change UID and GID of vagrant user to $1 and $2.
#
# Using this script can reduce permission-related difficulties when using the
# docker CI or development images.  Without this, if the host UID/GID does
# not match the container's (500/500), then ACLs have to be used to permit
# files created on the host to be read by the guest and vice-versa.
set -e

SRC_USER=vagrant
SRC_GROUP=vagrant

current_uid(){
  getent passwd $SRC_USER | cut -d: -f3
}

current_gid(){
  getent group $SRC_GROUP | cut -d: -f3
}

change_uid(){
  old_uid="$1"
  new_uid="$2"

  echo "Migrating $SRC_USER uid from $old_uid to $new_uid ..."

  (set -x; usermod -u $new_uid $SRC_USER; )
  (set -x; find / -xdev -user $old_uid -exec chown -h $new_uid {} \;; )
}

change_gid(){
  old_gid="$1"
  new_gid="$2"

  echo "Migrating $SRC_GROUP gid from $old_gid to $new_gid ..."

  (set -x; groupmod -g $new_gid $SRC_GROUP; )
  (set -x; find / -xdev -group $old_gid -exec chgrp -h $new_gid {} \;; )
}

run() {
  old_uid=$(current_uid)
  old_gid=$(current_gid)
  new_uid="$1"
  new_gid="$2"

  if test "$new_uid" != "$old_uid"; then
    change_uid $old_uid $new_uid
  fi
  if test "$new_gid" != "$old_gid"; then
    change_gid $old_gid $new_gid
  fi
}

run "$1" "$2"
