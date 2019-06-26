#!/bin/bash

set -eu

case $HOSTNAME in
mgeorg-retropie)
  REP_DIR=~/wakeup
  BRANCH=alarm
  ;;
scarfie-feeder)
  REP_DIR=~/wakeup
  BRANCH=feeder
  ;;
vigil)
  REP_DIR=~/wakeup
  BRANCH=laptop
  ;;
mgeorg-glaptop)
  REP_DIR=~/wakeup
  BRANCH=laptop
  ;;
*)
  echo "I don't know where I'm running"
  exit 1
  ;;
esac

cd $REP_DIR
if [[ "$(git diff --name-only)" != "" ]]; then
  echo "There are unstaged files, aborting."
  exit 1
fi

git checkout master
git merge $BRANCH
git checkout $BRANCH

