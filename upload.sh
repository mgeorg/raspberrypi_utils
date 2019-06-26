#!/bin/bash

set -eu

cd ~/wakeup/

if [[ "$(git diff --name-only)" != "" ]]; then
  echo "There are unstaged files, aborting."
  exit 1
fi

bash ~/wakeup/merge_master.sh

git checkout master

echo  "Merging master to feeder:"
ssh feeder bash ~/wakeup/merge_master.sh
echo  "pulling from feeder."
git pull feeder master

echo  "Merging master to pi:"
ssh pi bash ~/wakeup/merge_master.sh
echo  "pulling from pi."
git pull pi master

echo  "pushing to feeder"
git push feeder master
echo  "pushing to pi"
git push pi master

echo  "merging feeder"
ssh feeder bash ~/wakeup/merge_branch.sh
echo  "merging pi"
ssh pi bash ~/wakeup/merge_branch.sh
echo  "merging local pi"
bash ~/wakeup/merge_branch.sh

git checkout laptop

# Update github with new repo
git push github master
