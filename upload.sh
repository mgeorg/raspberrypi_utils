#!/bin/bash

set -eu

cd ~/raspberrypi/wakeup/

if [[ "$(git diff --name-only)" != "" ]]; then
  echo "There are unstaged files, aborting."
  exit 1
fi

bash ~/raspberrypi/wakeup/merge_master.sh

git checkout master

ssh feeder bash ~/wakeup/merge_master.sh
git pull feeder master

ssh pi bash ~/wakeup/merge_master.sh
git pull pi master

git push feeder master
git push pi master

ssh feeder bash ~/wakeup/merge_branch.sh
ssh pi bash ~/wakeup/merge_branch.sh
bash ~/raspberrypi/wakeup/merge_branch.sh

git checkout laptop

# Update github with new repo
git push github master
