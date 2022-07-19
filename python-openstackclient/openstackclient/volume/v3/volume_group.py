# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

from cinderclient import api_versions
from osc_lib.command import command
from osc_lib import exceptions
from osc_lib import utils

from openstackclient.i18n import _

LOG = logging.getLogger(__name__)


def _format_group(group):
    columns = (
        'id',
        'status',
        'name',
        'description',
        'group_type',
        'volume_types',
        'availability_zone',
        'created_at',
        'volumes',
        'group_snapshot_id',
        'source_group_id',
    )
    column_headers = (
        'ID',
        'Status',
        'Name',
        'Description',
        'Group Type',
        'Volume Types',
        'Availability Zone',
        'Created At',
        'Volumes',
        'Group Snapshot ID',
        'Source Group ID',
    )

    # TODO(stephenfin): Consider using a formatter for volume_types since it's
    # a list
    return (
        column_headers,
        utils.get_item_properties(
            group,
            columns,
        ),
    )


class CreateVolumeGroup(command.ShowOne):
    """Create a volume group.

    Generic volume groups enable you to create a group of volumes and manage
    them together.

    Generic volume groups are more flexible than consistency groups. Currently
    volume consistency groups only support consistent group snapshot. It
    cannot be extended easily to serve other purposes. A project may want to
    put volumes used in the same application together in a group so that it is
    easier to manage them together, and this group of volumes may or may not
    support consistent group snapshot. Generic volume group solve this problem.
    By decoupling the tight relationship between the group construct and the
    consistency concept, generic volume groups can be extended to support other
    features in the future.

    This command requires ``--os-volume-api-version`` 3.13 or greater.
    """

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            'volume_group_type',
            metavar='<volume_group_type>',
            help=_('Name or ID of volume group type to use.'),
        )
        parser.add_argument(
            'volume_types',
            metavar='<volume_type>',
            nargs='+',
            default=[],
            help=_('Name or ID of volume type(s) to use.'),
        )
        parser.add_argument(
            '--name',
            metavar='<name>',
            help=_('Name of the volume group.'),
        )
        parser.add_argument(
            '--description',
            metavar='<description>',
            help=_('Description of a volume group.')
        )
        parser.add_argument(
            '--availability-zone',
            metavar='<availability-zone>',
            help=_('Availability zone for volume group.'),
        )
        return parser

    def take_action(self, parsed_args):
        volume_client = self.app.client_manager.volume

        if volume_client.api_version < api_versions.APIVersion('3.13'):
            msg = _(
                "--os-volume-api-version 3.13 or greater is required to "
                "support the 'volume group create' command"
            )
            raise exceptions.CommandError(msg)

        volume_group_type = utils.find_resource(
            volume_client.group_types,
            parsed_args.volume_group_type,
        )

        volume_types = []
        for volume_type in parsed_args.volume_types:
            volume_types.append(
                utils.find_resource(
                    volume_client.volume_types,
                    volume_type,
                )
            )

        group = volume_client.groups.create(
            volume_group_type.id,
            ','.join(x.id for x in volume_types),
            parsed_args.name,
            parsed_args.description,
            availability_zone=parsed_args.availability_zone)

        group = volume_client.groups.get(group.id)

        return _format_group(group)


class DeleteVolumeGroup(command.Command):
    """Delete a volume group.

    This command requires ``--os-volume-api-version`` 3.13 or greater.
    """

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            'group',
            metavar='<group>',
            help=_('Name or ID of volume group to delete'),
        )
        parser.add_argument(
            '--force',
            action='store_true',
            default=False,
            help=_(
                'Delete the volume group even if it contains volumes. '
                'This will delete any remaining volumes in the group.',
            )
        )
        return parser

    def take_action(self, parsed_args):
        volume_client = self.app.client_manager.volume

        if volume_client.api_version < api_versions.APIVersion('3.13'):
            msg = _(
                "--os-volume-api-version 3.13 or greater is required to "
                "support the 'volume group delete' command"
            )
            raise exceptions.CommandError(msg)

        group = utils.find_resource(
            volume_client.groups,
            parsed_args.group,
        )

        volume_client.groups.delete(
            group.id, delete_volumes=parsed_args.force)


class SetVolumeGroup(command.ShowOne):
    """Update a volume group.

    This command requires ``--os-volume-api-version`` 3.13 or greater.
    """

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            'group',
            metavar='<group>',
            help=_('Name or ID of volume group.'),
        )
        parser.add_argument(
            '--name',
            metavar='<name>',
            help=_('New name for group.'),
        )
        parser.add_argument(
            '--description',
            metavar='<description>',
            help=_('New description for group.'),
        )
        parser.add_argument(
            '--enable-replication',
            action='store_true',
            dest='enable_replication',
            default=None,
            help=_(
                'Enable replication for group. '
                '(supported by --os-volume-api-version 3.38 or above)'
            ),
        )
        parser.add_argument(
            '--disable-replication',
            action='store_false',
            dest='enable_replication',
            help=_(
                'Disable replication for group. '
                '(supported by --os-volume-api-version 3.38 or above)'
            ),
        )
        return parser

    def take_action(self, parsed_args):
        volume_client = self.app.client_manager.volume

        if volume_client.api_version < api_versions.APIVersion('3.13'):
            msg = _(
                "--os-volume-api-version 3.13 or greater is required to "
                "support the 'volume group set' command"
            )
            raise exceptions.CommandError(msg)

        group = utils.find_resource(
            volume_client.groups,
            parsed_args.group,
        )

        if parsed_args.enable_replication is not None:
            if volume_client.api_version < api_versions.APIVersion('3.38'):
                msg = _(
                    "--os-volume-api-version 3.38 or greater is required to "
                    "support the '--enable-replication' or "
                    "'--disable-replication' options"
                )
                raise exceptions.CommandError(msg)

            if parsed_args.enable_replication:
                volume_client.groups.enable_replication(group.id)
            else:
                volume_client.groups.disable_replication(group.id)

        kwargs = {}

        if parsed_args.name is not None:
            kwargs['name'] = parsed_args.name

        if parsed_args.description is not None:
            kwargs['description'] = parsed_args.description

        if kwargs:
            group = volume_client.groups.update(group.id, **kwargs)

        return _format_group(group)


class ListVolumeGroup(command.Lister):
    """Lists all volume groups.

    This command requires ``--os-volume-api-version`` 3.13 or greater.
    """

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            '--all-projects',
            dest='all_projects',
            action='store_true',
            default=utils.env('ALL_PROJECTS', default=False),
            help=_('Shows details for all projects (admin only).'),
        )
        # TODO(stephenfin): Add once we have an equivalent command for
        # 'cinder list-filters'
        # parser.add_argument(
        #     '--filter',
        #     metavar='<key=value>',
        #     action=parseractions.KeyValueAction,
        #     dest='filters',
        #     help=_(
        #         "Filter key and value pairs. Use 'foo' to "
        #         "check enabled filters from server. Use 'key~=value' for "
        #         "inexact filtering if the key supports "
        #         "(supported by --os-volume-api-version 3.33 or above)"
        #     ),
        # )
        return parser

    def take_action(self, parsed_args):
        volume_client = self.app.client_manager.volume

        if volume_client.api_version < api_versions.APIVersion('3.13'):
            msg = _(
                "--os-volume-api-version 3.13 or greater is required to "
                "support the 'volume group list' command"
            )
            raise exceptions.CommandError(msg)

        search_opts = {
            'all_tenants': parsed_args.all_projects,
        }

        groups = volume_client.groups.list(
            search_opts=search_opts)

        column_headers = (
            'ID',
            'Status',
            'Name',
        )
        columns = (
            'id',
            'status',
            'name',
        )

        return (
            column_headers,
            (
                utils.get_item_properties(a, columns)
                for a in groups
            ),
        )


class ShowVolumeGroup(command.ShowOne):
    """Show detailed information for a volume group.

    This command requires ``--os-volume-api-version`` 3.13 or greater.
    """

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            'group',
            metavar='<group>',
            help=_('Name or ID of volume group.'),
        )
        parser.add_argument(
            '--volumes',
            action='store_true',
            dest='show_volumes',
            default=None,
            help=_(
                'Show volumes included in the group. '
                '(supported by --os-volume-api-version 3.25 or above)'
            ),
        )
        parser.add_argument(
            '--no-volumes',
            action='store_false',
            dest='show_volumes',
            help=_(
                'Do not show volumes included in the group. '
                '(supported by --os-volume-api-version 3.25 or above)'
            ),
        )
        parser.add_argument(
            '--replication-targets',
            action='store_true',
            dest='show_replication_targets',
            default=None,
            help=_(
                'Show replication targets for the group. '
                '(supported by --os-volume-api-version 3.38 or above)'
            ),
        )
        parser.add_argument(
            '--no-replication-targets',
            action='store_false',
            dest='show_replication_targets',
            help=_(
                'Do not show replication targets for the group. '
                '(supported by --os-volume-api-version 3.38 or above)'
            ),
        )

        return parser

    def take_action(self, parsed_args):
        volume_client = self.app.client_manager.volume

        if volume_client.api_version < api_versions.APIVersion('3.13'):
            msg = _(
                "--os-volume-api-version 3.13 or greater is required to "
                "support the 'volume group show' command"
            )
            raise exceptions.CommandError(msg)

        kwargs = {}

        if parsed_args.show_volumes is not None:
            if volume_client.api_version < api_versions.APIVersion('3.25'):
                msg = _(
                    "--os-volume-api-version 3.25 or greater is required to "
                    "support the '--(no-)volumes' option"
                )
                raise exceptions.CommandError(msg)

            kwargs['list_volume'] = parsed_args.show_volumes

        if parsed_args.show_replication_targets is not None:
            if volume_client.api_version < api_versions.APIVersion('3.38'):
                msg = _(
                    "--os-volume-api-version 3.38 or greater is required to "
                    "support the '--(no-)replication-targets' option"
                )
                raise exceptions.CommandError(msg)

        group = utils.find_resource(
            volume_client.groups,
            parsed_args.group,
        )

        group = volume_client.groups.show(group.id, **kwargs)

        if parsed_args.show_replication_targets:
            replication_targets = \
                volume_client.groups.list_replication_targets(group.id)

            group.replication_targets = replication_targets

        # TODO(stephenfin): Show replication targets
        return _format_group(group)


class FailoverVolumeGroup(command.Command):
    """Failover replication for a volume group.

    This command requires ``--os-volume-api-version`` 3.38 or greater.
    """

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            'group',
            metavar='<group>',
            help=_('Name or ID of volume group to failover replication for.'),
        )
        parser.add_argument(
            '--allow-attached-volume',
            action='store_true',
            dest='allow_attached_volume',
            default=False,
            help=_(
                'Allow group with attached volumes to be failed over.',
            )
        )
        parser.add_argument(
            '--disallow-attached-volume',
            action='store_false',
            dest='allow_attached_volume',
            default=False,
            help=_(
                'Disallow group with attached volumes to be failed over.',
            )
        )
        parser.add_argument(
            '--secondary-backend-id',
            metavar='<backend_id>',
            help=_('Secondary backend ID.'),
        )
        return parser

    def take_action(self, parsed_args):
        volume_client = self.app.client_manager.volume

        if volume_client.api_version < api_versions.APIVersion('3.38'):
            msg = _(
                "--os-volume-api-version 3.38 or greater is required to "
                "support the 'volume group failover' command"
            )
            raise exceptions.CommandError(msg)

        group = utils.find_resource(
            volume_client.groups,
            parsed_args.group,
        )

        volume_client.groups.failover_replication(
            group.id,
            allow_attached_volume=parsed_args.allow_attached_volume,
            secondary_backend_id=parsed_args.secondary_backend_id,
        )
