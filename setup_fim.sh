#!/usr/bin/env bash
# FIM Setup Script
# This script is intended to configure your local shell to use FIM from the docker image


FIM_DIR=${HOME}/.fim/
FIM_IMAGE="fim:latest"

function confirmation_prompt() {
# https://stackoverflow.com/questions/226703/how-do-i-prompt-for-yes-no-cancel-input-in-a-linux-shell-script/27875395#27875395
  RETURN=${1}
  shift
  MSG="$*"
  while true; do
    read -p "${MSG}" yn
    case $yn in
      [Yy]* ) break;;
      [Nn]* ) return ;; #exit $RETURN;;
      * ) echo "Please answer yes or no.";;
    esac
  done
}

mkdir -p ${FIM_DIR}

id=$(docker create ${FIM_IMAGE})
docker cp $id:/app/fortune.db ${FIM_DIR}/fortune.db
docker cp $id:/app/fimrc ${FIM_DIR}/fimrc
docker rm -v $id




FIM="alias fim=\"docker run -v ~/.fim/:/var/fim ${FIM_IMAGE} \""
FIM_DEBUG="alias fim_debug=\"docker run -it --entrypoint /bin/bash -v ~/.fim/:/var/fim ${FIM_IMAGE} \""


echo "To utilize this you must mount the directory: ${FIM_DIR} into your container

It is recommended to use th following alias:

    ${FIM}

"

{
confirmation_prompt 0 "Do you want to add the alias to your .bashrc? "
echo $FIM >> ~/.bashrc
echo $FIM_DEBUG >> ~/.bashrc
}

{
confirmation_prompt 0 "Do you want to add the alias to your .zshrc? "
echo $FIM >> ~/.zshrc
echo $FIM_DEBUG >> ~/.zshrc
}




