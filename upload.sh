#!/bin/bash

set -eu

cd ~/wakeup/

if [[ "$(git diff --name-only)" != "" ]]; then
  echo "There are unstaged files, aborting."
  exit 1
fi

echo  "#################################"
echo  "### Merging master on local   ###"
echo  "#################################"
bash ~/wakeup/merge_master.sh

git checkout master

echo  "#################################"
echo  "### Merging master to feeder: ###"
echo  "#################################"
ssh feeder bash ~/wakeup/merge_master.sh
echo  "#################################"
echo  "### Pulling from feeder.      ###"
echo  "#################################"
git pull feeder master

echo  "#################################"
echo  "### Merging master to pi      ###"
echo  "#################################"
ssh pi bash ~/wakeup/merge_master.sh
echo  "#################################"
echo  "### Pulling from pi           ###"
echo  "#################################"
git pull pi master

echo  "#################################"
echo  "### Pushing to feeder         ###"
echo  "#################################"
git push feeder master
echo  "#################################"
echo  "### Pushing to pi             ###"
echo  "#################################"
git push pi master

echo  "#################################"
echo  "### Merging to feeder         ###"
echo  "#################################"
ssh feeder bash ~/wakeup/merge_branch.sh
echo  "#################################"
echo  "### Merging to pi             ###"
echo  "#################################"
ssh pi bash ~/wakeup/merge_branch.sh
echo  "#################################"
echo  "### Merging local             ###"
echo  "#################################"
bash ~/wakeup/merge_branch.sh

git checkout laptop

echo  "#################################"
echo  "### Pushing to github         ###"
echo  "#################################"
# Update github with new repo
git push github master
