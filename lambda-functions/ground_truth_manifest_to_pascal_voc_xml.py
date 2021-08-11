# This lambda function is triggered by the EventBridge (CloudWatch Events) when a Ground Truth labelling job is marked as completed and an event is received by the EventBridge
# SageMaker Ground Truth Labeling Job State Change where LabelingJobStatus == Completed
# This lambda should then trigger the next lambda function in the sequence

import json
import string
import glob
from pathlib import Path
import boto3

full_template = string.Template("""
<annotation>
    <folder>images</folder>
    <filename>${image_filename}</filename>
    <size>
        <width>${image_width}</width>
        <height>${image_height}</height>
        <depth>3</depth>
    </size>
    <segmented>0</segmented>
    ${bounding_box_objects}
</annotation>"""
                                )

bndbox_template = string.Template("""<object>
        <name>${label}</name>
        <pose>Unspecified</pose>
        <truncated>0</truncated>
        <occluded>0</occluded>
        <difficult>0</difficult>
        <bndbox> 
            <xmin>${xmin}</xmin>
            <ymin>${ymin}</ymin>
            <xmax>${xmax}</xmax>
            <ymax>${ymax}</ymax>
        </bndbox>
    </object>"""
                                  )


class BoundingBoxXml:
    def __init__(self, label: str, top: int, left: int, height: int, width: int):
        self.label = label
        self.xmin = left
        self.ymin = top
        self.xmax = left + width
        self.ymax = top + height
        self.xml = ""

    def generate_bndbox_object(self):
        self.xml = bndbox_template.substitute(
            label=self.label, xmin=self.xmin, ymin=self.ymin, xmax=self.xmax, ymax=self.ymax)


def lambda_handler(event, context):
    # TODO implement
    source_bucket_name = <<INSERT YOUR SOURCE BUCKET HERE>>
    output_bucket_name = <<INSERT YOUR OUTPUT BUCKET HERE>>
    s3_client = boto3.client("s3")
    s3_resource = boto3.resource("s3")
    bucket = s3_resource.Bucket(source_bucket_name)
    storage_annotations_bucket = s3_resource.Bucket(output_bucket_name)

    response = s3_client.list_objects(Bucket=bucket_name,
                                      Prefix='facemask-detection',
                                      Delimiter='/'
                                      )

    # looping each folder that starts with facemask-detection
    for o in response.get('CommonPrefixes'):
        annotation_parent_folder = o.get('Prefix')
        annotation_json_folder = annotation_parent_folder + \
            "annotations/consolidated-annotation/consolidation-request/iteration-1"

        for json_object in bucket.objects.filter(Prefix=annotation_json_folder):
            s3_json_object = s3_client.get_object(
                Bucket=source_bucket_name, Key=json_object.key)
            dataset_objects = json.loads(
                s3_json_object['Body'].read().decode('utf-8'))

            for dataset_object in dataset_objects:
                image_uri = Path(dataset_object['dataObject']['s3Uri'])
                image_filename = image_uri.name
                xml_filename = image_filename.split(".")[0] + ".xml"

                # Assume that there is only 1 annotated data since we only have 1 worker
                bndbox_string = dataset_object['annotations'][0]['annotationData']['content']
                bndbox_json = json.loads(bndbox_string)
                bndbox_objects = bndbox_json['annotatedResult']['boundingBoxes']

                inner_bndbox_xml = ""
                for i in range(len(bndbox_objects)):
                    bndbox_object = bndbox_objects[i]
                    bndbox_xml = BoundingBoxXml(bndbox_object['label'],
                                                bndbox_object['top'],
                                                bndbox_object['left'],
                                                bndbox_object['height'],
                                                bndbox_object['width']
                                                )
                    bndbox_xml.generate_bndbox_object()

                    if i == 0:
                        inner_bndbox_xml += bndbox_xml.xml
                    else:
                        inner_bndbox_xml += '\n\t' + bndbox_xml.xml

                image_properties = bndbox_json['annotatedResult']['inputImageProperties']

                xml_output = full_template.substitute(
                    image_filename=image_filename, image_width=image_properties['width'], image_height=image_properties['height'], bounding_box_objects=inner_bndbox_xml)

                encoded_string = xml_output.encode("utf-8")
                s3_resource.Bucket(bucket_name).put_object(
                    Key=xml_filename, Body=encoded_string)

        # to copy over GT annotations folder to another bucket and removing them from current bucket
        for obj in bucket.objects.filter(Prefix=annotation_parent_folder):
            old_source = {'Bucket': bucket_name,
                          'Key': obj.key}
            new_obj = storage_annotations_bucket.Object(obj.key)
            new_obj.copy(old_source)
            s3_resource.Object(bucket_name, obj.key).delete()

    return {
        'statusCode': 200,
        'body': json.dumps('Successfully converted bounding boxes to XML format')
    }
