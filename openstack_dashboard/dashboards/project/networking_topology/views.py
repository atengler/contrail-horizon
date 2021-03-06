# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2013 NTT MCL Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse  # noqa
from django.views.generic import TemplateView  # noqa
from django.views.generic import View  # noqa

from openstack_dashboard import api

from contrail_openstack_dashboard.openstack_dashboard.dashboards.project.networking_topology.instances \
    import tables as instances_tables
from contrail_openstack_dashboard.openstack_dashboard.dashboards.project.networking_topology.ports \
    import tables as ports_tables
from contrail_openstack_dashboard.openstack_dashboard.dashboards.project.networking_topology.routers \
    import tables as routers_tables

from openstack_dashboard.dashboards.project.instances import\
    views as i_views
from openstack_dashboard.dashboards.project.instances.workflows import\
    create_instance as i_workflows
from contrail_openstack_dashboard.openstack_dashboard.dashboards.project.networking import\
    views as n_views
from contrail_openstack_dashboard.openstack_dashboard.dashboards.project.networking import\
    workflows as n_workflows
from contrail_openstack_dashboard.openstack_dashboard.dashboards.project.l3routers import\
    views as r_views


class NTCreateRouterView(r_views.CreateView):
    template_name = 'project/networking_topology/create_router.html'
    success_url = reverse_lazy("horizon:project:networking_topology:index")


class NTCreateNetwork(n_workflows.CreateNetwork):
    def get_success_url(self):
        return reverse("horizon:project:networking_topology:index")

    def get_failure_url(self):
        return reverse("horizon:project:networking_topology:index")


class NTCreateNetworkView(n_views.CreateView):
    workflow_class = NTCreateNetwork


class NTLaunchInstance(i_workflows.LaunchInstance):
    success_url = "horizon:project:networking_topology:index"


class NTLaunchInstanceView(i_views.LaunchInstanceView):
    workflow_class = NTLaunchInstance


class InstanceView(i_views.IndexView):
    table_class = instances_tables.InstancesTable
    template_name = 'project/networking_topology/iframe.html'


class RouterView(r_views.IndexView):
    table_class = routers_tables.RoutersTable
    template_name = 'project/networking_topology/iframe.html'


class RouterDetailView(r_views.DetailView):
    table_classes = (ports_tables.PortsTable, )
    template_name = 'project/networking_topology/iframe.html'

    def get_interfaces_data(self):
        pass


class NetworkTopologyView(TemplateView):
    template_name = 'project/networking_topology/index.html'

    def _has_permission(self, policy):
        has_permission = True
        policy_check = getattr(settings, "POLICY_CHECK_FUNCTION", None)

        if policy_check:
            has_permission = policy_check(policy, self.request)

        return has_permission

    def get_context_data(self, **kwargs):
        context = super(NetworkTopologyView, self).get_context_data(**kwargs)
        network_config = getattr(settings, 'OPENSTACK_NEUTRON_NETWORK', {})

        context['launch_instance_allowed'] = self._has_permission(
            (("compute", "compute:create"),))
        context['create_network_allowed'] = self._has_permission(
            (("network", "create_network"),))
        context['create_router_allowed'] = (
            network_config.get('enable_router', True) and
            self._has_permission((("network", "create_router"),)))
        context['console_type'] = getattr(
            settings, 'CONSOLE_TYPE', 'AUTO')
        return context


class JSONView(View):

    @property
    def is_router_enabled(self):
        network_config = getattr(settings, 'OPENSTACK_NEUTRON_NETWORK', {})
        return network_config.get('enable_router', True)

    def add_resource_url(self, view, resources):
        tenant_id = self.request.user.tenant_id
        for resource in resources:
            if (resource.get('tenant_id')
                    and tenant_id != resource.get('tenant_id')):
                continue
            resource['url'] = reverse(view, None, [str(resource['id'])])

    def _check_router_external_port(self, ports, router_id, network_id):
        for port in ports:
            if (port['network_id'] == network_id
                    and port['device_id'] == router_id):
                return True
        return False

    def _get_servers(self, request):
        # Get nova data
        try:
            servers, more = api.nova.server_list(request)
        except Exception:
            servers = []
        console_type = getattr(settings, 'CONSOLE_TYPE', 'AUTO')
        if console_type == 'SPICE':
            console = 'spice'
        else:
            console = 'vnc'
        data = [{'name': server.name,
                 'status': server.status,
                 'console': console,
                 'task': getattr(server, 'OS-EXT-STS:task_state'),
                 'id': server.id} for server in servers]
        self.add_resource_url('horizon:project:instances:detail', data)
        return data

    def _get_networks(self, request):
        # Get neutron data
        # if we didn't specify tenant_id, all networks shown as admin user.
        # so it is need to specify the networks. However there is no need to
        # specify tenant_id for subnet. The subnet which belongs to the public
        # network is needed to draw subnet information on public network.
        try:
            neutron_networks = api.neutron.network_list_for_tenant(
                request,
                request.user.tenant_id)
        except Exception:
            neutron_networks = []
        networks = [{'name': network.name,
                     'id': network.id,
                     'subnets': [{'cidr': subnet.cidr}
                                 for subnet in network.subnets],
                     'router:external': network['router:external']}
                    for network in neutron_networks]
        self.add_resource_url('horizon:project:networking:detail',
                              networks)

        # Add public networks to the networks list
        if self.is_router_enabled:
            try:
                neutron_public_networks = api.neutron.network_list(
                    request,
                    **{'router:external': True})
            except Exception:
                neutron_public_networks = []
            my_network_ids = [net['id'] for net in networks]
            for publicnet in neutron_public_networks:
                if publicnet.id in my_network_ids:
                    continue
                try:
                    subnets = [{'cidr': subnet.cidr}
                               for subnet in publicnet.subnets]
                except Exception:
                    subnets = []
                networks.append({
                    'name': publicnet.name,
                    'id': publicnet.id,
                    'subnets': subnets,
                    'router:external': publicnet['router:external']})

        return sorted(networks,
                      key=lambda x: x.get('router:external'),
                      reverse=True)

    def _get_routers(self, request):
        if not self.is_router_enabled:
            return []
        try:
            neutron_routers = api.neutron.router_list(
                request,
                tenant_id=request.user.tenant_id)
        except Exception:
            neutron_routers = []

        routers = [{'id': router.id,
                    'name': router.name,
                    'status': router.status,
                    'external_gateway_info': router.external_gateway_info}
            for router in neutron_routers]
        self.add_resource_url('horizon:project:l3routers:detail', routers)
        return routers

    def _get_ports(self, request):
        try:
            neutron_ports = api.neutron.port_list(request)
        except Exception:
            neutron_ports = []

        ports = [{'id': port.id,
                  'network_id': port.network_id,
                  'device_id': port.device_id,
                  'fixed_ips': port.fixed_ips,
                  'device_owner': port.device_owner,
                  'status': port.status}
                 for port in neutron_ports]
        self.add_resource_url('horizon:project:networking:ports:detail',
                              ports)
        return ports

    def _prepare_gateway_ports(self, routers, ports):
        # user can't see port on external network. so we are
        # adding fake port based on router information
        for router in routers:
            external_gateway_info = router.get('external_gateway_info')
            if not external_gateway_info:
                continue
            external_network = external_gateway_info.get(
                'network_id')
            if not external_network:
                continue
            if self._check_router_external_port(ports,
                                                router['id'],
                                                external_network):
                continue
            fake_port = {'id': 'gateway%s' % external_network,
                         'network_id': external_network,
                         'device_id': router['id'],
                         'fixed_ips': []}
            ports.append(fake_port)

    def get(self, request, *args, **kwargs):
        data = {'servers': self._get_servers(request),
                'networks': self._get_networks(request),
                'ports': self._get_ports(request),
                'routers': self._get_routers(request)}
        self._prepare_gateway_ports(data['routers'], data['ports'])
        json_string = json.dumps(data, ensure_ascii=False)
        return HttpResponse(json_string, content_type='text/json')
