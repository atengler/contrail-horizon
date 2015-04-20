# Copyright 2012,  Nachi Ueno,  NTT MCL,  Inc.
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

from contrail_openstack_dashboard.openstack_dashboard.dashboards.admin.\
    l3routers.extensions.routerrules import tables as rrtbl
from contrail_openstack_dashboard.openstack_dashboard.dashboards.admin.l3routers.ports import tables as ptbl
from contrail_openstack_dashboard.openstack_dashboard.dashboards.project.l3routers.extensions.routerrules\
    import tabs as rr_tabs
from contrail_openstack_dashboard.openstack_dashboard.dashboards.project.l3routers import tabs as r_tabs


class RouterRulesTab(rr_tabs.RouterRulesTab):
    table_classes = (rrtbl.RouterRulesTable,)


class InterfacesTab(r_tabs.InterfacesTab):
    table_classes = (ptbl.PortsTable,)


class RouterDetailTabs(r_tabs.RouterDetailTabs):
    slug = "router_details"
    tabs = (InterfacesTab, rr_tabs.RouterRulesTab)
    sticky = True
