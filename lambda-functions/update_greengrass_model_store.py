# This function updates your model store component with the most updated model given by sagemaker
# This function invokes a code pipeline to eventually update the inference component and deployment of the model
# If you are managing multiple models, remember to pass a tag to determine which deployment to update

import json
import boto3
import ast
import urllib3
http = urllib3.PoolManager()

COMPONENT_BUCKET = <<FILL THIS UP>>
COMPONENT_FILE = <<FILL THIS UP>>
INFERENCE_COMPONENT_NAME = <<FILL THIS UP>>
MODEL_COMPONENT_NAME = <<FILL THIS UP>>

inference_component_arn = None
model_component_version = ""


def lambda_handler(event, context):

    gg2 = boto3.client('greengrassv2')
    s3 = boto3.resource('s3')
    codepipeline = boto3.client('codepipeline')

    try:
        all_components = gg2.list_components(maxResults=5)
        for comp in all_components['components']:
            if comp['componentName'] == MODEL_COMPONENT_NAME:
                model_component_arn = comp['latestVersion']['arn']

        model_component_json = gg2.get_component(
            recipeOutputFormat='JSON', arn=model_component_arn)['recipe'].decode('utf8')
        model_comp = ast.literal_eval(model_component_json)

        # increment component version
        model_comp_version_num = model_comp['ComponentVersion']
        if model_comp_version_num[-1] == 9:
            new_version_mid = int(model_comp_version_num[2]) + 1
            new_comp_version = model_comp_version_num[0:2] + \
                str(new_version_mid) + ".0"
        else:
            new_comp_version = model_comp_version_num[0:-
                                                      1] + str(int(model_comp_version_num[-1]) + 1)

        print("Component before update")
        print(model_comp)

        model_comp['ComponentVersion'] = new_comp_version

        # remove exisiting SHA digest
        del model_comp['Manifests'][0]['Artifacts'][0]['Digest']
        del model_comp['Manifests'][0]['Artifacts'][0]['Algorithm']

        print("Component after update")
        print(model_comp)

        print("Updating component now")
        comp_update = gg2.create_component_version(
            inlineRecipe=json.dumps(model_comp))
        print(comp_update)

        comp_update['creationTimestamp'] = comp_update['creationTimestamp'].isoformat()

        if len(comp_update['status']['errors']) > 0:
            print("Error in updating model component")

        else:

            exec_id = codepipeline.start_pipeline_execution(
                name='GG_INFERENCE_DEPLOY')
            print("Codepipeline execution started: {}".format(exec_id))
            print("Exiting..")

    except Exception as e:
        print("Error in updating component: {}".format(e))
