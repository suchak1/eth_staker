import boto3
import logging
from datetime import datetime, timedelta
from Constants import DEPLOY_ENV, AWS, SNAPSHOT_DAYS, MAX_SNAPSHOT_DAYS


class Snapshot:
    def __init__(self) -> None:
        self.tag = f'{DEPLOY_ENV}_staking_snapshot'
        self.ec2 = boto3.client('ec2')
        self.ssm = boto3.client('ssm')
        self.auto = boto3.client('autoscaling')
        self.ecs = boto3.client('ecs')
        if AWS:
            self.volume_id = self.get_prefix_id('VOLUME')
            self.instance_id = self.get_prefix_id('INSTANCE')

    def is_older_than(self, snapshot, num_days):
        created = self.get_snapshot_time(snapshot)
        now = datetime.utcnow()
        actual_delta = now - created
        max_delta = timedelta(days=num_days)
        return actual_delta > max_delta

    def force_create(self):
        snapshot = self.ec2.create_snapshot(
            VolumeId=self.volume_id,
            TagSpecifications=[
                {
                    'ResourceType': 'snapshot',
                    'Tags': [{'Key': 'type', 'Value': self.tag}]
                }
            ]
        )
        return snapshot

    def create(self, curr_snapshots):
        all_snapshots_are_old = all(
            [self.is_older_than(snapshot, SNAPSHOT_DAYS)
             for snapshot in curr_snapshots]
        )
        if all_snapshots_are_old:
            # Don't need to wait for 'completed' status
            # As soon as function returns,
            # old state is preserved while snapshot is in progress
            snapshot = self.force_create()
            self.put_param(snapshot['SnapshotId'])
            return snapshot

    def get_prefix_id(self, prefix):
        with open(f'/mnt/ebs/{prefix}_ID', 'r') as file:
            id = file.read().strip()
        return id

    def get_snapshots(self):
        snapshots = self.ec2.describe_snapshots(
            Filters=[
                {
                    'Name': 'tag:type',
                    'Values': [self.tag]
                },
            ],
            OwnerIds=['self'],
        )['Snapshots']

        return snapshots

    def get_exceptions(self):
        exceptions = set([
            exception for exception in [
                         self.get_param(),
                         self.get_curr_snapshot_id()
                         ] if exception
        ])
        return exceptions

    def get_snapshot_time(self, snapshot):
        return snapshot['StartTime'].replace(tzinfo=None)

    def find_most_recent(self, curr_snapshots):
        if not curr_snapshots:
            return None
        most_recent_idx = 0
        self.get_snapshot_time(curr_snapshots[0])
        for idx, snapshot in enumerate(curr_snapshots):
            if self.get_snapshot_time(snapshot) > self.get_snapshot_time(curr_snapshots[most_recent_idx]):
                most_recent_idx = idx

        return curr_snapshots[most_recent_idx]

    def purge(self, curr_snapshots, exceptions):

        purgeable = [
            snapshot for snapshot in curr_snapshots if self.is_older_than(
                snapshot, MAX_SNAPSHOT_DAYS
            ) and snapshot['SnapshotId'] not in exceptions
        ]

        for snapshot in purgeable:
            self.ec2.delete_snapshot(
                SnapshotId=snapshot['SnapshotId'],
            )

    def put_param(self, snapshot_id):
        self.ssm.put_parameter(
            Name=self.tag,
            Value=snapshot_id,
            Type='String',
            Overwrite=True,
            Tier='Standard',
            DataType='text'
        )

    def get_param(self):
        val = None
        try:
            # Add existing snapshot id from ssm
            val = self.ssm.get_parameter(
                Name=self.tag)['Parameter']['Value']
        except Exception as e:
            logging.exception(e)
        return val

    def get_curr_snapshot_id(self):
        val = None
        try:
            # Add snapshot id from current instance's launch template
            if AWS:
                launch_template = self.ec2.get_launch_template_data(
                    InstanceId=self.instance_id)
                for device in launch_template['LaunchTemplateData']['BlockDeviceMappings']:
                    if device['DeviceName'] == '/dev/sdx':
                        val = device['Ebs']['SnapshotId']
                        break
        except Exception as e:
            logging.exception(e)

        return val

    def update(self):
        curr_snapshots = self.get_snapshots()
        most_recent = self.find_most_recent(curr_snapshots)
        recent_snapshot_id = most_recent['SnapshotId']
        self.put_param(recent_snapshot_id)
        template_name = f'{DEPLOY_ENV}_launch_template'
        launch_template = self.ec2.describe_launch_template_versions(
            LaunchTemplateName=template_name, Versions=['$Latest'])['LaunchTemplateVersions'][0]
        for device in launch_template['LaunchTemplateData']['BlockDeviceMappings']:
            if device['DeviceName'] == '/dev/sdx':
                vol = device
                curr_snapshot_id = device['Ebs']['SnapshotId']
                break
        template_version = str(launch_template['VersionNumber'])
        if curr_snapshot_id != recent_snapshot_id:
            vol['Ebs']['SnapshotId'] = recent_snapshot_id
            template_version = str(self.ec2.create_launch_template_version(
                LaunchTemplateName=template_name, SourceVersion=template_version, LaunchTemplateData={'BlockDeviceMappings': [vol]})['LaunchTemplateVersions']['VersionNumber'])
        asg_name = f'ECS_{DEPLOY_ENV}_staking_ASG'
        asg = self.auto.describe_auto_scaling_groups(
            AutoScalingGroupNames=[asg_name])['AutoScalingGroups'][0]
        update_asg = asg['LaunchTemplate']['Version'] != template_version
        instance = [instance for instance in asg['Instances']
                    if instance['InstanceId'] == self.instance_id][0]
        refresh_instance = instance['LaunchTemplate']['Version'] != template_version
        if update_asg:
            self.auto.update_auto_scaling_group(
                AutoScalingGroupName=asg_name,
                LaunchTemplate={
                    'LaunchTemplateName': template_name,
                    'Version': '$Latest'
                }
            )
        if update_asg or refresh_instance:
            return True

        return False

    def instance_is_draining(self):
        cluster_name = f'{DEPLOY_ENV}-staking-cluster'
        container_instance_arns = self.ecs.list_container_instances(
            cluster=cluster_name)['containerInstanceArns']
        container_instances = self.ecs.describe_container_instances(
            cluster=cluster_name, containerInstances=container_instance_arns)['containerInstances']
        container_instance = [
            instance for instance in container_instances if instance['ec2InstanceId'] == self.instance_id][0]
        status = container_instance['status']
        return status == 'DRAINING'

    def backup(self):
        curr_snapshots = self.get_snapshots()
        exceptions = self.get_exceptions()
        snapshot = self.create(curr_snapshots)
        self.purge(curr_snapshots, exceptions)
        return snapshot or self.find_most_recent(curr_snapshots)

    def terminate(self):
        self.ec2.terminate_instances(InstanceIds=[self.instance_id])
