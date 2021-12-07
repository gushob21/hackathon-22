#!/bin/bash -x
SCRIPT_PATH="$(
  cd "$(dirname "$0")" >/dev/null 2>&1
  pwd -P
)"

export GOOGLE_PROJECT=${GCP_PROJECT_ID}
export GCLOUD_USER=${GCP_PROJECT_ID}@${GCP_PROJECT_ID}.iam.gserviceaccount.com

export HOME=/root
export WORKDIR=${HOME}/techcon

mkdir -p ${WORKDIR}

source /snap/google-cloud-sdk/current/completion.bash.inc
source /snap/google-cloud-sdk/current/path.bash.inc

#if [ ${PREWARM_TYPE} == "VARS_ONLY" ]; then
#  echo "Prepare initial vars.sh file"
#  gsutil mb -p ${GOOGLE_PROJECT} gs://${GOOGLE_PROJECT}
#
#  user_count=$(env | egrep '^GC_USERNAME_[0-9]+=' | wc -l)
#  for user_num in $(seq 1 $user_count); do
#    username_env_var="GC_USERNAME_${user_num}"
#    CURRENT_GCLOUD_USER=${!username_env_var}
#    CURRENT_GCLOUD_USER_LOGIN="${CURRENT_GCLOUD_USER%%@*}"
#
#    vars_filename="vars.sh.${CURRENT_GCLOUD_USER_LOGIN}"
#    cat <<EOF >${WORKDIR}/${vars_file}
#export GCLOUD_USER=${CURRENT_GCLOUD_USER}
#export GOOGLE_PROJECT=${GCP_PROJECT_ID}
#EOF
#
#    gsutil cp ${WORKDIR}/${vars_filename} gs://$GOOGLE_PROJECT/${vars_filename}
#  done
#fi

build_lab_exit_code=0
if [ ${PREWARM_TYPE} == "FULL" ]; then
  apt-get --quiet update
  apt-get --quiet install -y jq python-is-python3 python3-pip
  pip install --upgrade pip
  pip install --quiet -r ${SCRIPT_PATH}/requirements.txt

  python ${SCRIPT_PATH}/create_pipeline.py ${GCP_PROJECT_ID}
  build_lab_exit_code=$?
fi

if [ "${build_lab_exit_code}" -eq 0 ]; then
  gcloud beta runtime-config configs variables set \
    success/qwiklabs-prewarm-instance-waiter \
    success --config-name prewarm-runtime-config
else
  gcloud beta runtime-config configs variables set \
    failure/qwiklabs-prewarm-instance-waiter \
    failure --config-name prewarm-runtime-config
fi

gcloud compute instances delete qwiklabs-prewarm-instance --quiet --zone=${GCP_ZONE}


