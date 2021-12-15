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


build_lab_exit_code=0
if [ ${PREWARM_TYPE} == "FULL" ]; then

#Enable notebook API
#gcloud services enable notebooks.googleapis.com
#Create notebook
#gcloud notebooks instances create hackathon-22 \
#--vm-image-project=deeplearning-platform-release \
#--vm-image-family=common-cu110-notebooks  \
#--machine-type=n2-standard-16 --location=us-central1-a

if [ $? -eq 0 ] ; then
  echo "Notebook created successfully" >> /tmp/logs
else
  echo "can not create notebook.Exiting" >> /tmp/logs
  exit 1
fi

  apt-get --quiet update
  apt-get --quiet install -y jq python-is-python3 python3-pip
  apt install python3.8-venv
  python -m venv /root/venv
  source /root/venv/bin/activate
  pip install --upgrade pip
  pip install --quiet -r ${SCRIPT_PATH}/requirements.txt

  python ${SCRIPT_PATH}/create_pipeline.py ${GCP_PROJECT_ID} ${SCRIPT_PATH}/pipeline.json >> /tmp/logs 2>&1
  build_lab_exit_code=$?
fi

echo "Out of the loop with exit code ${build_lab_exit_code}" >> /tmp/logs

if [ "${build_lab_exit_code}" -eq 0 ]; then
  gcloud beta runtime-config configs variables set \
    success/qwiklabs-prewarm-instance-waiter \
    success --config-name prewarm-runtime-config
else
  gcloud beta runtime-config configs variables set \
    failure/qwiklabs-prewarm-instance-waiter \
    failure --config-name prewarm-runtime-config
fi

#gcloud compute instances delete qwiklabs-prewarm-instance --quiet --zone=${GCP_ZONE}


