from google.cloud import aiplatform
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
from datetime import datetime
from google.cloud import storage
import googleapiclient.discovery
import time
import sys


def enable_apis(project_id,api):
  """Enable APIS in project."""
  print("HERE FOR " + api)
  credentials = GoogleCredentials.get_application_default()
  project = 'projects/' + project_id
  service = discovery.build('serviceusage', 'v1', credentials=credentials)
  request = service.services().enable(name=project + "/services/" + api + ".googleapis.com")
  counter = 0
  checkInterval = 5
  threshold = 60
  try:
    response = request.execute()
  except Exception as e:
    print(e)
    exit(1)
  time.sleep(5)

  if 'done' in response:
    while  not response['done'] and counter < threshold:
      print("Waiting for the API to be enabled")
      time.sleep(5)
      counter += checkInterval
  if counter > threshold:
    print('Can not enable compute API.Exiting')
    exit(1)
  else:
    print("Enabled " + api + ".googleapis.com")


def create_gcs(bucket_name):
  """Create GCS."""

  storage_client = storage.Client()
  bucket_name = bucket_name
  bucket = storage_client.create_bucket(bucket_name)
  print("Bucket {} created.".format(bucket.name))

def copy_sample_dataset(source_bucket_name,destination_bucket_name,source_blob_name,destination_blob_name):
  """Copy sampel data set."""

  storage_client = storage.Client()
  source_bucket = storage_client.get_bucket(source_bucket_name)
  source_blob = source_bucket.blob(source_blob_name)
  destination_bucket = storage_client.get_bucket(destination_bucket_name)

  # copy to new destination
  new_blob = source_bucket.copy_blob(
      source_blob, destination_bucket, destination_blob_name)



def get_policy(project_id,version=1):
  """Gets IAM policy for a project."""

  credentials = GoogleCredentials.get_application_default()
  service = googleapiclient.discovery.build(
      "cloudresourcemanager", "v1", credentials=credentials
  )
  policy = (
      service.projects()
        .getIamPolicy(
          resource=project_id,
          body={"options": {"requestedPolicyVersion": version}},
      )
        .execute()
  )
  return policy

def get_project_number(project_id):
  """Get project number."""

  credentials = GoogleCredentials.get_application_default()
  service = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
  request = service.projects().get(projectId=project_id)
  try:
    response = request.execute()
    return(response['projectNumber'])
  except Exception as e:
    print(e)
    exit(1)

def get_compute_sa(project_number):
  """Derive compute service account name."""

  return("serviceAccount:" + project_number + "-compute@developer.gserviceaccount.com")


def modify_policy_add_role(policy, role, member):
  """Adds a new role binding to a policy."""

  binding = {"role": role, "members": [member]}
  policy["bindings"].append(binding)
  return policy

def set_policy(project_id, policy):
  """Sets IAM policy for a project."""

  credentials = GoogleCredentials.get_application_default()
  service = googleapiclient.discovery.build(
      "cloudresourcemanager", "v1", credentials=credentials
  )

  policy = (
      service.projects()
        .setIamPolicy(resource=project_id, body={"policy": policy})
        .execute()
  )
  print(policy)
  return policy

def run_vertex_pipeline(parameter_values,pipeline_root,service_account):
  """Create vertex pipeline."""

  # Instantiate PipelineJob object
  pl = aiplatform.PipelineJob(display_name="accelerate-hackaton-2022", enable_caching=False, template_path="pipeline.json", parameter_values=parameter_values, pipeline_root=pipeline_root)

  # Execute pipeline in Vertex and monitor until completion
  pl.run(service_account=service_account,sync=True)
  # Email address of service account to use for the pipeline run
  # You must have iam.serviceAccounts.actAs permission on the service account to use it



if __name__ == "__main__":

  if len(sys.argv) != 2 :
    print("Script need only one parameter - project id")
    exit(1)
  project = sys.argv[1]
  print(project)
  apis = ["bigquery", "bigquerystorage",  "compute", "storage-api", "storage-component", "storage", "aiplatform", "ml"]
  gcs = project + "hackathon-" + datetime.today().strftime('%Y-%m-%d-%H-%M-%S')
  source_bucket_name = "cloud-samples-data"
  source_blob_name = "vertex-ai/community-content/datasets/abalone/abalone.data"
  #source_blob_name = "abalone.data"
  destination_blob_name = "data/abalone.csv"

  #Setting up parameters for Vertex pipeline
  storage_viewer_role = "roles/storage.objectViewer"
  storage_creater_role = "roles/storage.objectCreator"
  bq_dataset = "j90wipxexhrgq3cquanc5"
  bq_location = "US"
  bqml_model_export_location = "gs://" + gcs + "/artifacts/bqml/"
  bqml_serving_container_image_uri = "us-docker.pkg.dev/vertex-ai/prediction/tf2-cpu.2-6:latest"
  gcs_batch_prediction_output_prefix = "gs://" + gcs + "/predictions/"
  gcs_input_file_uri = "gs://" + gcs + "/data/abalone.csv"
  region = "us-central1"
  test_dataset_folder = "gs://" + gcs + "/data/test_dataset"
  thresholds_dict_str = {"rmse": 20.0}
  parameter_values = { "bq_dataset": bq_dataset ,"bq_location": bq_location, "bqml_model_export_location": bqml_model_export_location, "bqml_serving_container_image_uri": bqml_serving_container_image_uri, "gcs_batch_prediction_output_prefix": gcs_batch_prediction_output_prefix, "gcs_input_file_uri": gcs_input_file_uri, "project": project, "region": region, "test_dataset_folder": test_dataset_folder, "thresholds_dict_str": thresholds_dict_str }
  pipeline_root = "gs://" + gcs
  print("Enabling required APIs")
  for api in apis:
    enable_apis(project,api)

  print("Creating GCS")
  create_gcs(gcs)

  print("Copying test data set into the bucket")
  copy_sample_dataset(source_bucket_name,gcs,source_blob_name,destination_blob_name)

  print("Getting IAM policy on the projects")
  policy = get_policy(project)
  project_number = get_project_number(project)
  compute_sa = get_compute_sa(project_number)
  print("Preparing policy modification")
  new_policy = modify_policy_add_role(policy,storage_viewer_role,compute_sa)
  final_policy = modify_policy_add_role(new_policy,storage_creater_role,compute_sa)
  print("Updating the policy to add objectViewer and objectCreator role to compute SA")
  updated_policy=set_policy(project,final_policy)
  run_vertex_pipeline(parameter_values,pipeline_root,compute_sa.split(':')[1])

