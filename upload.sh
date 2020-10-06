#!/bin/bash

set -eu

cd ~/wakeup/

ENABLE_PI=0
ENABLE_FEEDER=1

if [[ "$(git diff --name-only)" != "" ]]; then
  echo "There are unstaged files, aborting."
  exit 1
fi

echo  "#################################"
echo  "### Merging master on local   ###"
echo  "#################################"
bash ~/wakeup/merge_master.sh

git checkout master

if [[ "${ENABLE_FEEDER}" == "1" ]]
then
  echo  "#################################"
  echo  "### Merging master to feeder: ###"
  echo  "#################################"
  ssh feeder bash ~/wakeup/merge_master.sh
  echo  "#################################"
  echo  "### Pulling from feeder.      ###"
  echo  "#################################"
  git pull feeder master
else
  echo  "#################################"
  echo  "### SKIPPING Feeder           ###"
  echo  "#################################"
fi

if [[ "${ENABLE_PI}" == "1" ]]
then
  echo  "#################################"
  echo  "### Merging master to pi      ###"
  echo  "#################################"
  ssh pi bash ~/wakeup/merge_master.sh
  echo  "#################################"
  echo  "### Pulling from pi           ###"
  echo  "#################################"
  git pull pi master
else
  echo  "#################################"
  echo  "### SKIPPING Pi               ###"
  echo  "#################################"
fi

if [[ "${ENABLE_FEEDER}" == "1" ]]
then
  echo  "#################################"
  echo  "### Pushing to feeder         ###"
  echo  "#################################"
  git push feeder master
fi
if [[ "${ENABLE_PI}" == "1" ]]
then
  echo  "#################################"
  echo  "### Pushing to pi             ###"
  echo  "#################################"
  git push pi master
fi

if [[ "${ENABLE_FEEDER}" == "1" ]]
then
  echo  "#################################"
  echo  "### Merging to feeder         ###"
  echo  "#################################"
  ssh feeder bash ~/wakeup/merge_branch.sh
fi
if [[ "${ENABLE_PI}" == "1" ]]
  then
  echo  "#################################"
  echo  "### Merging to pi             ###"
  echo  "#################################"
  ssh pi bash ~/wakeup/merge_branch.sh
fi
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
