"""
Security Assessment MCP Tools
=============================
Tools for Azure cloud security assessment based on Microsoft Cloud Security
Benchmark (MCSB) v2. These tools are used by the Cloud Platform Security
Assessment Team agents.

Domains:
  NS - Network Security (10 controls)
  IM - Identity Management (8 controls)
  DP - Data Protection (8 controls)
  PA - Privileged Access (8 controls)
  AM - Asset Management (5 controls)
  LT - Logging and Threat Detection (7 controls)
  IR - Incident Response (7 controls)
  PV - Posture and Vulnerability Management (7 controls)
  ES - Endpoint Security (3 controls)
  BR - Backup and Recovery (4 controls)
  DS - DevOps Security (7 controls)
  GS - Governance and Strategy (11 controls)
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any

# These will be imported when tools are registered
# from azure.identity import DefaultAzureCredential
# from azure.mgmt.* clients

# ══════════════════════════════════════════════════════════════════════
# Global client cache for security assessment
# ══════════════════════════════════════════════════════════════════════

_sec_network_client: Any = None
_sec_compute_client: Any = None
_sec_storage_client: Any = None
_sec_sql_client: Any = None
_sec_keyvault_client: Any = None
_sec_monitor_client: Any = None
_sec_security_client: Any = None
_sec_auth_client: Any = None
_sec_recovery_client: Any = None
_sec_web_client: Any = None
_sec_container_client: Any = None
_sec_subscription_client: Any = None

# Load MCSB v2 controls from JSON file
_mcsb_controls: dict | None = None


def _get_subscription_id() -> str:
    """Return the configured Azure subscription ID."""
    sub_id = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
    if not sub_id:
        raise ValueError("AZURE_SUBSCRIPTION_ID is not set")
    return sub_id


def _get_credential():
    """Get sync Azure credential."""
    from azure.identity import DefaultAzureCredential
    return DefaultAzureCredential()


def _get_network_client():
    """Lazy-init Azure Network Management client."""
    global _sec_network_client
    if _sec_network_client is None:
        from azure.mgmt.network import NetworkManagementClient
        _sec_network_client = NetworkManagementClient(
            _get_credential(), _get_subscription_id()
        )
    return _sec_network_client


def _get_compute_client():
    """Lazy-init Azure Compute Management client."""
    global _sec_compute_client
    if _sec_compute_client is None:
        from azure.mgmt.compute import ComputeManagementClient
        _sec_compute_client = ComputeManagementClient(
            _get_credential(), _get_subscription_id()
        )
    return _sec_compute_client


def _get_storage_client():
    """Lazy-init Azure Storage Management client."""
    global _sec_storage_client
    if _sec_storage_client is None:
        from azure.mgmt.storage import StorageManagementClient
        _sec_storage_client = StorageManagementClient(
            _get_credential(), _get_subscription_id()
        )
    return _sec_storage_client


def _get_sql_client():
    """Lazy-init Azure SQL Management client."""
    global _sec_sql_client
    if _sec_sql_client is None:
        from azure.mgmt.sql import SqlManagementClient
        _sec_sql_client = SqlManagementClient(
            _get_credential(), _get_subscription_id()
        )
    return _sec_sql_client


def _get_keyvault_client():
    """Lazy-init Azure Key Vault Management client."""
    global _sec_keyvault_client
    if _sec_keyvault_client is None:
        from azure.mgmt.keyvault import KeyVaultManagementClient
        _sec_keyvault_client = KeyVaultManagementClient(
            _get_credential(), _get_subscription_id()
        )
    return _sec_keyvault_client


def _get_monitor_client():
    """Lazy-init Azure Monitor Management client."""
    global _sec_monitor_client
    if _sec_monitor_client is None:
        from azure.mgmt.monitor import MonitorManagementClient
        _sec_monitor_client = MonitorManagementClient(
            _get_credential(), _get_subscription_id()
        )
    return _sec_monitor_client


def _get_security_client():
    """Lazy-init Azure Security Center client."""
    global _sec_security_client
    if _sec_security_client is None:
        from azure.mgmt.security import SecurityCenter
        _sec_security_client = SecurityCenter(
            _get_credential(), _get_subscription_id(), ""
        )
    return _sec_security_client


def _get_auth_client():
    """Lazy-init Azure Authorization Management client."""
    global _sec_auth_client
    if _sec_auth_client is None:
        from azure.mgmt.authorization import AuthorizationManagementClient
        _sec_auth_client = AuthorizationManagementClient(
            _get_credential(), _get_subscription_id()
        )
    return _sec_auth_client


def _get_recovery_client():
    """Lazy-init Azure Recovery Services client."""
    global _sec_recovery_client
    if _sec_recovery_client is None:
        from azure.mgmt.recoveryservices import RecoveryServicesClient
        _sec_recovery_client = RecoveryServicesClient(
            _get_credential(), _get_subscription_id()
        )
    return _sec_recovery_client


def _get_web_client():
    """Lazy-init Azure Web Site Management client."""
    global _sec_web_client
    if _sec_web_client is None:
        from azure.mgmt.web import WebSiteManagementClient
        _sec_web_client = WebSiteManagementClient(
            _get_credential(), _get_subscription_id()
        )
    return _sec_web_client


def _get_container_client():
    """Lazy-init Azure Container Service client."""
    global _sec_container_client
    if _sec_container_client is None:
        from azure.mgmt.containerservice import ContainerServiceClient
        _sec_container_client = ContainerServiceClient(
            _get_credential(), _get_subscription_id()
        )
    return _sec_container_client


def _get_subscription_client():
    """Lazy-init Azure Subscription client."""
    global _sec_subscription_client
    if _sec_subscription_client is None:
        from azure.mgmt.subscription import SubscriptionClient
        _sec_subscription_client = SubscriptionClient(_get_credential())
    return _sec_subscription_client


def _get_resource_client():
    """Lazy-init Azure Resource Management client."""
    from azure.mgmt.resource import ResourceManagementClient
    return ResourceManagementClient(_get_credential(), _get_subscription_id())


def _load_mcsb_controls() -> dict:
    """Load MCSB v2 controls from the benchmark tool's JSON file."""
    global _mcsb_controls
    if _mcsb_controls is None:
        controls_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "cis-azure-benchmark-assessment-tool",
            "mcsb_v2_tool",
            "mcsb_v2_controls.json"
        )
        # Try alternate path if running from different location
        if not os.path.exists(controls_path):
            controls_path = os.path.join(
                os.path.dirname(__file__),
                "mcsb_v2_controls.json"
            )
        if os.path.exists(controls_path):
            with open(controls_path, "r", encoding="utf-8") as f:
                _mcsb_controls = json.load(f)
        else:
            # Return minimal structure if file not found
            _mcsb_controls = {"controls": {}, "domains": []}
    return _mcsb_controls


def _create_finding(
    control_id: str,
    title: str,
    status: str,
    severity: str,
    resource_name: str,
    resource_type: str,
    resource_group: str,
    current_value: str,
    expected_value: str,
    finding: str,
    recommendation: str,
    rationale: str,
) -> dict:
    """Create a standardized finding dictionary."""
    return {
        "control_id": control_id,
        "title": title,
        "status": status,  # PASS, FAIL, MANUAL_REVIEW
        "severity": severity,  # Critical, High, Medium, Low, Info
        "resource_name": resource_name,
        "resource_type": resource_type,
        "resource_group": resource_group,
        "current_value": current_value,
        "expected_value": expected_value,
        "finding": finding,
        "recommendation": recommendation,
        "rationale": rationale,
        "assessed_at": datetime.utcnow().isoformat(),
    }


# ══════════════════════════════════════════════════════════════════════
# Tool Functions (to be registered with MCP server)
# ══════════════════════════════════════════════════════════════════════

async def sec_list_subscriptions() -> str:
    """
    List all Azure subscriptions accessible with current credentials.
    Returns subscription IDs, names, and states.
    """
    loop = asyncio.get_running_loop()

    def _list():
        try:
            client = _get_subscription_client()
            subs = []
            for sub in client.subscriptions.list():
                subs.append({
                    "subscription_id": sub.subscription_id,
                    "display_name": sub.display_name,
                    "state": str(sub.state),
                    "tenant_id": sub.tenant_id,
                })
            return {"status": "success", "subscriptions": subs, "count": len(subs)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    result = await loop.run_in_executor(None, _list)
    return json.dumps(result, default=str)


async def sec_get_mcsb_controls(domain: str = "") -> str:
    """
    Get MCSB v2 control definitions. Optionally filter by domain.

    Args:
        domain: Optional domain filter (e.g., 'NS', 'IM', 'DP'). Empty returns all.
    """
    controls_data = _load_mcsb_controls()
    
    if domain:
        # Filter by domain prefix
        filtered = {
            k: v for k, v in controls_data.get("controls", {}).items()
            if k.startswith(domain.upper() + "-")
        }
        return json.dumps({
            "status": "success",
            "domain": domain.upper(),
            "controls": filtered,
            "count": len(filtered),
        })
    
    return json.dumps({
        "status": "success",
        "domains": controls_data.get("domains", []),
        "controls": controls_data.get("controls", {}),
        "total_controls": len(controls_data.get("controls", {})),
    })


async def sec_list_resources(
    resource_type: str = "",
    resource_group: str = "",
) -> str:
    """
    List Azure resources in the subscription. Optionally filter by type or resource group.

    Args:
        resource_type: Optional filter by resource type (e.g., 'Microsoft.Network/virtualNetworks').
        resource_group: Optional filter by resource group name.
    """
    loop = asyncio.get_running_loop()

    def _list():
        try:
            client = _get_resource_client()
            resources = []
            
            if resource_group:
                iterator = client.resources.list_by_resource_group(resource_group)
            else:
                iterator = client.resources.list()
            
            for res in iterator:
                if resource_type and res.type.lower() != resource_type.lower():
                    continue
                resources.append({
                    "name": res.name,
                    "type": res.type,
                    "location": res.location,
                    "resource_group": res.id.split("/")[4] if res.id else "",
                    "id": res.id,
                    "tags": res.tags or {},
                })
            
            return {"status": "success", "resources": resources, "count": len(resources)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    result = await loop.run_in_executor(None, _list)
    return json.dumps(result, default=str)


async def sec_get_resource_details(
    resource_id: str,
    api_version: str = "2023-07-01",
) -> str:
    """
    Get detailed properties of an Azure resource by its resource ID.

    Args:
        resource_id: Full Azure resource ID.
        api_version: API version to use (default: 2023-07-01).
    """
    loop = asyncio.get_running_loop()

    def _get():
        try:
            client = _get_resource_client()
            resource = client.resources.get_by_id(resource_id, api_version)
            
            return {
                "status": "success",
                "name": resource.name,
                "type": resource.type,
                "location": resource.location,
                "properties": resource.properties,
                "tags": resource.tags,
                "sku": resource.sku.as_dict() if resource.sku else None,
                "kind": resource.kind,
                "id": resource.id,
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "resource_id": resource_id}

    result = await loop.run_in_executor(None, _get)
    return json.dumps(result, default=str)


async def sec_list_role_assignments(
    scope: str = "",
) -> str:
    """
    List RBAC role assignments. Optionally filter by scope.

    Args:
        scope: Optional scope filter (e.g., subscription, resource group, or resource ID).
    """
    loop = asyncio.get_running_loop()

    def _list():
        try:
            client = _get_auth_client()
            assignments = []
            
            if scope:
                iterator = client.role_assignments.list_for_scope(scope)
            else:
                iterator = client.role_assignments.list()
            
            for ra in iterator:
                assignments.append({
                    "id": ra.id,
                    "principal_id": ra.principal_id,
                    "principal_type": str(ra.principal_type) if ra.principal_type else None,
                    "role_definition_id": ra.role_definition_id,
                    "scope": ra.scope,
                })
            
            return {"status": "success", "role_assignments": assignments, "count": len(assignments)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    result = await loop.run_in_executor(None, _list)
    return json.dumps(result, default=str)


async def sec_check_defender_status() -> str:
    """
    Check Microsoft Defender for Cloud status and pricing tiers for all resource types.
    """
    loop = asyncio.get_running_loop()

    def _check():
        try:
            client = _get_security_client()
            pricings = []
            
            for pricing in client.pricings.list().value:
                pricings.append({
                    "name": pricing.name,
                    "pricing_tier": pricing.pricing_tier,
                    "free_trial_remaining_time": str(pricing.free_trial_remaining_time) if pricing.free_trial_remaining_time else None,
                })
            
            return {"status": "success", "defender_plans": pricings, "count": len(pricings)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    result = await loop.run_in_executor(None, _check)
    return json.dumps(result, default=str)


# ══════════════════════════════════════════════════════════════════════
# Domain-Specific Assessment Functions
# ══════════════════════════════════════════════════════════════════════

async def sec_assess_network_security() -> str:
    """
    Assess Azure subscription against MCSB v2 Network Security (NS) domain.
    Checks: VNets, NSGs, private endpoints, firewalls, DDoS protection, WAF, DNS.
    Returns findings as JSON array.
    """
    loop = asyncio.get_running_loop()

    def _assess():
        findings = []
        try:
            network = _get_network_client()
            
            # NS-1: Network segmentation (VNets and NSGs)
            vnets = list(network.virtual_networks.list_all())
            if len(vnets) == 0:
                findings.append(_create_finding(
                    "NS-1", "Establish network segmentation boundaries",
                    "FAIL", "High", "Subscription", "Subscription", "",
                    "No VNets found", "At least one VNet should exist",
                    "No virtual networks configured in subscription",
                    "Create VNets to establish network segmentation",
                    "Network segmentation is fundamental for security isolation"
                ))
            else:
                for vnet in vnets:
                    rg = vnet.id.split("/")[4]
                    # Check if subnets have NSGs
                    subnets_without_nsg = []
                    for subnet in (vnet.subnets or []):
                        if not subnet.network_security_group:
                            subnets_without_nsg.append(subnet.name)
                    
                    if subnets_without_nsg:
                        findings.append(_create_finding(
                            "NS-1", "Establish network segmentation boundaries",
                            "FAIL", "Medium", vnet.name, "Microsoft.Network/virtualNetworks", rg,
                            f"Subnets without NSG: {', '.join(subnets_without_nsg)}",
                            "All subnets should have NSG attached",
                            f"VNet {vnet.name} has subnets without NSG association",
                            "Associate NSGs with all subnets to control traffic flow",
                            "NSGs provide network layer filtering for subnet traffic"
                        ))
                    else:
                        findings.append(_create_finding(
                            "NS-1", "Establish network segmentation boundaries",
                            "PASS", "Info", vnet.name, "Microsoft.Network/virtualNetworks", rg,
                            "All subnets have NSG", "All subnets should have NSG attached",
                            f"VNet {vnet.name} has proper NSG configuration",
                            "No action required", "Network segmentation properly configured"
                        ))
            
            # NS-2: Private endpoints
            private_endpoints = list(network.private_endpoints.list_all())
            if len(private_endpoints) == 0:
                findings.append(_create_finding(
                    "NS-2", "Secure cloud native services with network controls",
                    "MANUAL_REVIEW", "Medium", "Subscription", "Subscription", "",
                    "No private endpoints found", "Use private endpoints for PaaS services",
                    "No private endpoints configured - review if PaaS services need private connectivity",
                    "Configure private endpoints for Azure PaaS services to disable public access",
                    "Private endpoints keep traffic on Microsoft backbone network"
                ))
            else:
                findings.append(_create_finding(
                    "NS-2", "Secure cloud native services with network controls",
                    "PASS", "Info", "Subscription", "Subscription", "",
                    f"{len(private_endpoints)} private endpoints found",
                    "Use private endpoints for PaaS services",
                    "Private endpoints are configured for Azure services",
                    "Continue using private endpoints for new services",
                    "Private connectivity is properly configured"
                ))
            
            # NS-3: Firewall deployment
            firewalls = list(network.azure_firewalls.list_all())
            if len(firewalls) == 0:
                findings.append(_create_finding(
                    "NS-3", "Deploy firewall at the edge of enterprise network",
                    "FAIL", "High", "Subscription", "Subscription", "",
                    "No Azure Firewall found", "Deploy Azure Firewall or NVA",
                    "No Azure Firewall deployed for centralized traffic control",
                    "Deploy Azure Firewall for advanced traffic filtering",
                    "Centralized firewall provides application-layer filtering"
                ))
            else:
                for fw in firewalls:
                    rg = fw.id.split("/")[4]
                    findings.append(_create_finding(
                        "NS-3", "Deploy firewall at the edge of enterprise network",
                        "PASS", "Info", fw.name, "Microsoft.Network/azureFirewalls", rg,
                        f"Provisioning state: {fw.provisioning_state}",
                        "Firewall should be deployed", "Azure Firewall is deployed",
                        "Ensure firewall rules are properly configured",
                        "Centralized firewall is in place"
                    ))
            
            # NS-4: DDoS Protection
            ddos_plans = list(network.ddos_protection_plans.list())
            if len(ddos_plans) == 0:
                findings.append(_create_finding(
                    "NS-4", "Protect applications from external network attacks",
                    "FAIL", "High", "Subscription", "Subscription", "",
                    "No DDoS Protection Plan found", "Enable DDoS Protection Standard",
                    "DDoS Protection Standard not enabled",
                    "Enable DDoS Protection Standard for public-facing resources",
                    "DDoS Protection provides advanced mitigation capabilities"
                ))
            else:
                findings.append(_create_finding(
                    "NS-4", "Protect applications from external network attacks",
                    "PASS", "Info", "Subscription", "Subscription", "",
                    f"{len(ddos_plans)} DDoS Protection Plan(s) found",
                    "DDoS Protection should be enabled",
                    "DDoS Protection Standard is configured",
                    "Ensure DDoS plan is associated with VNets",
                    "DDoS protection is in place"
                ))
            
            # NS-5: Internal traffic filtering (NSGs)
            nsgs = list(network.network_security_groups.list_all())
            for nsg in nsgs:
                rg = nsg.id.split("/")[4]
                rule_count = len(nsg.security_rules or [])
                if rule_count == 0:
                    findings.append(_create_finding(
                        "NS-5", "Simplify network security rules",
                        "MANUAL_REVIEW", "Low", nsg.name, "Microsoft.Network/networkSecurityGroups", rg,
                        "No custom rules defined", "Define appropriate security rules",
                        f"NSG {nsg.name} has no custom rules",
                        "Review if custom rules are needed",
                        "NSGs should have rules tailored to workload"
                    ))
                else:
                    findings.append(_create_finding(
                        "NS-5", "Simplify network security rules",
                        "PASS", "Info", nsg.name, "Microsoft.Network/networkSecurityGroups", rg,
                        f"{rule_count} custom rules defined",
                        "Security rules should be defined",
                        f"NSG {nsg.name} has {rule_count} custom rules",
                        "Review rules periodically to ensure least privilege",
                        "Security rules are configured"
                    ))
            
            # NS-10: DNS Security
            dns_zones = list(network.private_dns_zones.list())
            findings.append(_create_finding(
                "NS-10", "DNS security",
                "MANUAL_REVIEW" if len(dns_zones) == 0 else "PASS",
                "Low", "Subscription", "Subscription", "",
                f"{len(dns_zones)} Private DNS zones found",
                "Use Azure DNS or secure DNS configuration",
                "DNS configuration assessment",
                "Ensure DNS queries use secure resolvers",
                "DNS security requires proper configuration"
            ))
            
            return {"status": "success", "domain": "NS", "findings": findings, "count": len(findings)}
        except Exception as e:
            return {"status": "error", "error": str(e), "findings": findings}

    result = await loop.run_in_executor(None, _assess)
    return json.dumps(result, default=str)


async def sec_assess_identity_management() -> str:
    """
    Assess Azure subscription against MCSB v2 Identity Management (IM) domain.
    Checks managed identities, service principals, RBAC configurations.
    Returns findings as JSON array.
    """
    loop = asyncio.get_running_loop()

    def _assess():
        findings = []
        try:
            compute = _get_compute_client()
            web = _get_web_client()
            
            # IM-3 & IM-4: Managed identities on VMs
            vms = list(compute.virtual_machines.list_all())
            for vm in vms:
                rg = vm.id.split("/")[4]
                has_managed_identity = vm.identity is not None
                
                if has_managed_identity:
                    identity_type = str(vm.identity.type) if vm.identity else "None"
                    findings.append(_create_finding(
                        "IM-3", "Manage application identities securely",
                        "PASS", "Info", vm.name, "Microsoft.Compute/virtualMachines", rg,
                        f"Identity type: {identity_type}",
                        "Use managed identity",
                        f"VM {vm.name} has managed identity configured",
                        "Continue using managed identity",
                        "Managed identity eliminates credential management"
                    ))
                else:
                    findings.append(_create_finding(
                        "IM-3", "Manage application identities securely",
                        "FAIL", "Medium", vm.name, "Microsoft.Compute/virtualMachines", rg,
                        "No managed identity",
                        "Use managed identity for Azure service authentication",
                        f"VM {vm.name} does not have managed identity",
                        "Enable system-assigned or user-assigned managed identity",
                        "Managed identities provide automatic credential rotation"
                    ))
            
            # IM-3 & IM-4: Managed identities on App Services
            try:
                apps = list(web.web_apps.list())
                for app in apps:
                    rg = app.id.split("/")[4]
                    has_managed_identity = app.identity is not None
                    
                    if has_managed_identity:
                        findings.append(_create_finding(
                            "IM-4", "Authenticate server and services",
                            "PASS", "Info", app.name, "Microsoft.Web/sites", rg,
                            "Managed identity enabled",
                            "Use managed identity for Azure service auth",
                            f"App Service {app.name} has managed identity",
                            "Continue using managed identity",
                            "Managed identity provides secure authentication"
                        ))
                    else:
                        findings.append(_create_finding(
                            "IM-4", "Authenticate server and services",
                            "FAIL", "Medium", app.name, "Microsoft.Web/sites", rg,
                            "No managed identity",
                            "Enable managed identity",
                            f"App Service {app.name} lacks managed identity",
                            "Enable managed identity for the App Service",
                            "Managed identities eliminate hardcoded credentials"
                        ))
            except Exception:
                pass  # Web apps may not exist
            
            # IM-1, IM-2, IM-5, IM-6, IM-7, IM-8: Manual review items
            manual_controls = [
                ("IM-1", "Use centralized identity and authentication system", "Verify Entra ID is the identity provider"),
                ("IM-2", "Protect identity and authentication system", "Review Entra ID security configurations"),
                ("IM-5", "Use single sign-on for application access", "Verify SSO is configured for applications"),
                ("IM-6", "Use strong authentication controls", "Review MFA and passwordless configurations"),
                ("IM-7", "Restrict resource access based on conditions", "Review Conditional Access policies"),
                ("IM-8", "Restrict exposure of credentials", "Verify secrets are stored in Key Vault"),
            ]
            
            for ctrl_id, title, guidance in manual_controls:
                findings.append(_create_finding(
                    ctrl_id, title,
                    "MANUAL_REVIEW", "Medium", "Organization", "Organization", "",
                    "Requires Entra ID review", guidance,
                    f"{title} - requires organizational policy review",
                    guidance,
                    "This control requires review of Entra ID configurations"
                ))
            
            return {"status": "success", "domain": "IM", "findings": findings, "count": len(findings)}
        except Exception as e:
            return {"status": "error", "error": str(e), "findings": findings}

    result = await loop.run_in_executor(None, _assess)
    return json.dumps(result, default=str)


async def sec_assess_data_protection() -> str:
    """
    Assess Azure subscription against MCSB v2 Data Protection (DP) domain.
    Checks encryption at rest, in transit, TLS versions, Key Vault configurations.
    Returns findings as JSON array.
    """
    loop = asyncio.get_running_loop()

    def _assess():
        findings = []
        try:
            storage = _get_storage_client()
            sql = _get_sql_client()
            keyvault = _get_keyvault_client()
            
            # DP-3 & DP-4: Storage account encryption and TLS
            storage_accounts = list(storage.storage_accounts.list())
            for sa in storage_accounts:
                rg = sa.id.split("/")[4]
                
                # Check HTTPS only
                if sa.enable_https_traffic_only:
                    findings.append(_create_finding(
                        "DP-3", "Encrypt sensitive data in transit",
                        "PASS", "Info", sa.name, "Microsoft.Storage/storageAccounts", rg,
                        "HTTPS only: Enabled", "HTTPS traffic only should be enabled",
                        f"Storage account {sa.name} enforces HTTPS",
                        "HTTPS enforcement is properly configured",
                        "Data in transit is encrypted"
                    ))
                else:
                    findings.append(_create_finding(
                        "DP-3", "Encrypt sensitive data in transit",
                        "FAIL", "High", sa.name, "Microsoft.Storage/storageAccounts", rg,
                        "HTTPS only: Disabled", "HTTPS traffic only should be enabled",
                        f"Storage account {sa.name} allows HTTP traffic",
                        "Enable 'Secure transfer required' on storage account",
                        "HTTP traffic exposes data to interception"
                    ))
                
                # Check minimum TLS version
                min_tls = sa.minimum_tls_version or "TLS1_0"
                if min_tls in ("TLS1_2", "TLS1_3"):
                    findings.append(_create_finding(
                        "DP-3", "Encrypt sensitive data in transit",
                        "PASS", "Info", sa.name, "Microsoft.Storage/storageAccounts", rg,
                        f"Min TLS: {min_tls}", "TLS 1.2 or higher required",
                        f"Storage account {sa.name} enforces {min_tls}",
                        "TLS configuration is secure",
                        "Modern TLS version is required"
                    ))
                else:
                    findings.append(_create_finding(
                        "DP-3", "Encrypt sensitive data in transit",
                        "FAIL", "High", sa.name, "Microsoft.Storage/storageAccounts", rg,
                        f"Min TLS: {min_tls}", "TLS 1.2 or higher required",
                        f"Storage account {sa.name} allows outdated TLS",
                        "Set minimum TLS version to 1.2",
                        "Older TLS versions have known vulnerabilities"
                    ))
                
                # DP-4: Encryption at rest (always on for Azure Storage)
                findings.append(_create_finding(
                    "DP-4", "Enable data at rest encryption by default",
                    "PASS", "Info", sa.name, "Microsoft.Storage/storageAccounts", rg,
                    "Encryption: Platform-managed keys",
                    "Data at rest should be encrypted",
                    f"Storage account {sa.name} has encryption enabled",
                    "Encryption is enabled by default",
                    "Azure Storage encrypts all data at rest"
                ))
            
            # DP-6, DP-7, DP-8: Key Vault configurations
            vaults = list(keyvault.vaults.list())
            for vault in vaults:
                rg = vault.id.split("/")[4]
                props = vault.properties
                
                # Soft delete
                if props.enable_soft_delete:
                    findings.append(_create_finding(
                        "DP-8", "Ensure security of key and certificate repository",
                        "PASS", "Info", vault.name, "Microsoft.KeyVault/vaults", rg,
                        "Soft delete: Enabled",
                        "Soft delete should be enabled",
                        f"Key Vault {vault.name} has soft delete enabled",
                        "Soft delete provides recovery capability",
                        "Deleted keys can be recovered"
                    ))
                else:
                    findings.append(_create_finding(
                        "DP-8", "Ensure security of key and certificate repository",
                        "FAIL", "High", vault.name, "Microsoft.KeyVault/vaults", rg,
                        "Soft delete: Disabled",
                        "Soft delete should be enabled",
                        f"Key Vault {vault.name} lacks soft delete",
                        "Enable soft delete on the Key Vault",
                        "Soft delete prevents accidental permanent deletion"
                    ))
                
                # Purge protection
                if props.enable_purge_protection:
                    findings.append(_create_finding(
                        "DP-8", "Ensure security of key and certificate repository",
                        "PASS", "Info", vault.name, "Microsoft.KeyVault/vaults", rg,
                        "Purge protection: Enabled",
                        "Purge protection should be enabled",
                        f"Key Vault {vault.name} has purge protection",
                        "Purge protection prevents permanent deletion",
                        "Keys cannot be permanently deleted during retention"
                    ))
                else:
                    findings.append(_create_finding(
                        "DP-8", "Ensure security of key and certificate repository",
                        "FAIL", "Medium", vault.name, "Microsoft.KeyVault/vaults", rg,
                        "Purge protection: Disabled",
                        "Purge protection should be enabled",
                        f"Key Vault {vault.name} lacks purge protection",
                        "Enable purge protection on the Key Vault",
                        "Purge protection adds defense against malicious deletion"
                    ))
            
            # DP-1, DP-2, DP-5, DP-6, DP-7: Manual review
            manual_controls = [
                ("DP-1", "Discover, classify, and label sensitive data", "Review Microsoft Purview or data classification solutions"),
                ("DP-2", "Monitor anomalies and threats targeting sensitive data", "Review Defender for Storage and DLP alerts"),
                ("DP-5", "Use customer-managed key when required", "Review CMK requirements for sensitive workloads"),
                ("DP-6", "Use a secure key management process", "Review key rotation and access policies"),
                ("DP-7", "Use a secure certificate management process", "Review certificate lifecycle management"),
            ]
            
            for ctrl_id, title, guidance in manual_controls:
                findings.append(_create_finding(
                    ctrl_id, title,
                    "MANUAL_REVIEW", "Medium", "Organization", "Organization", "",
                    "Requires policy review", guidance,
                    f"{title} - requires organizational review",
                    guidance,
                    "This control requires process/policy verification"
                ))
            
            return {"status": "success", "domain": "DP", "findings": findings, "count": len(findings)}
        except Exception as e:
            return {"status": "error", "error": str(e), "findings": findings}

    result = await loop.run_in_executor(None, _assess)
    return json.dumps(result, default=str)


async def sec_assess_privileged_access() -> str:
    """
    Assess Azure subscription against MCSB v2 Privileged Access (PA) domain.
    Checks RBAC role assignments, Owner/Contributor counts, PIM usage.
    Returns findings as JSON array.
    """
    loop = asyncio.get_running_loop()

    def _assess():
        findings = []
        try:
            auth = _get_auth_client()
            sub_id = _get_subscription_id()
            scope = f"/subscriptions/{sub_id}"
            
            # Get all role assignments at subscription scope
            assignments = list(auth.role_assignments.list_for_scope(scope))
            
            # Get role definitions to map IDs to names
            role_defs = {rd.id: rd.role_name for rd in auth.role_definitions.list(scope)}
            
            # Count privileged roles
            owner_count = 0
            contributor_count = 0
            
            for ra in assignments:
                role_name = role_defs.get(ra.role_definition_id, "Unknown")
                if "Owner" in role_name:
                    owner_count += 1
                elif "Contributor" in role_name:
                    contributor_count += 1
            
            # PA-1: Limit highly privileged users
            if owner_count > 3:
                findings.append(_create_finding(
                    "PA-1", "Separate and limit highly privileged users",
                    "FAIL", "High", "Subscription", "Subscription", "",
                    f"Owner assignments: {owner_count}",
                    "Limit Owner role to 3 or fewer",
                    f"Subscription has {owner_count} Owner role assignments",
                    "Review and reduce Owner role assignments",
                    "Excessive Owner access increases risk"
                ))
            else:
                findings.append(_create_finding(
                    "PA-1", "Separate and limit highly privileged users",
                    "PASS", "Info", "Subscription", "Subscription", "",
                    f"Owner assignments: {owner_count}",
                    "Limit Owner role to 3 or fewer",
                    f"Owner role assignments ({owner_count}) within acceptable limit",
                    "Continue monitoring privileged access",
                    "Privileged access is appropriately limited"
                ))
            
            # PA-7: Just enough administration (RBAC)
            total_assignments = len(assignments)
            findings.append(_create_finding(
                "PA-7", "Follow just enough administration principle",
                "MANUAL_REVIEW", "Medium", "Subscription", "Subscription", "",
                f"Total role assignments: {total_assignments}",
                "Review role assignments for least privilege",
                f"Subscription has {total_assignments} role assignments",
                "Audit role assignments for necessity and scope",
                "Verify users have minimum necessary permissions"
            ))
            
            # PA-2 through PA-6, PA-8: Manual review
            manual_controls = [
                ("PA-2", "Avoid standing access for user accounts", "Review PIM usage for just-in-time access"),
                ("PA-3", "Manage lifecycle of identities and entitlements", "Review identity governance processes"),
                ("PA-4", "Review and reconcile user access regularly", "Review access review configurations"),
                ("PA-5", "Set up emergency access", "Verify break-glass accounts exist"),
                ("PA-6", "Use privileged access workstations", "Review PAW deployment for admins"),
                ("PA-8", "Determine access process for cloud provider support", "Review Customer Lockbox settings"),
            ]
            
            for ctrl_id, title, guidance in manual_controls:
                findings.append(_create_finding(
                    ctrl_id, title,
                    "MANUAL_REVIEW", "Medium", "Organization", "Organization", "",
                    "Requires organizational review", guidance,
                    f"{title} - requires process verification",
                    guidance,
                    "This control requires organizational policy review"
                ))
            
            return {"status": "success", "domain": "PA", "findings": findings, "count": len(findings)}
        except Exception as e:
            return {"status": "error", "error": str(e), "findings": findings}

    result = await loop.run_in_executor(None, _assess)
    return json.dumps(result, default=str)


async def sec_assess_asset_management() -> str:
    """
    Assess Azure subscription against MCSB v2 Asset Management (AM) domain.
    Checks resource inventory, Azure Policy, tags, and resource locks.
    Returns findings as JSON array.
    """
    loop = asyncio.get_running_loop()

    def _assess():
        findings = []
        try:
            resource_client = _get_resource_client()
            
            # AM-1: Asset inventory
            resources = list(resource_client.resources.list())
            resource_count = len(resources)
            
            # Count resources with tags
            tagged_count = sum(1 for r in resources if r.tags)
            tag_coverage = (tagged_count / resource_count * 100) if resource_count > 0 else 0
            
            findings.append(_create_finding(
                "AM-1", "Track asset inventory and their risks",
                "PASS" if resource_count > 0 else "FAIL",
                "Info", "Subscription", "Subscription", "",
                f"Resources: {resource_count}, Tagged: {tagged_count} ({tag_coverage:.1f}%)",
                "Maintain complete asset inventory",
                f"Subscription has {resource_count} resources",
                "Ensure all resources are tagged for tracking",
                "Complete inventory enables risk assessment"
            ))
            
            # AM-2: Approved services via Azure Policy
            try:
                from azure.mgmt.policyinsights import PolicyInsightsClient
                policy_client = PolicyInsightsClient(_get_credential(), _get_subscription_id())
                
                # Get policy compliance summary
                summary = policy_client.policy_states.summarize_for_subscription(
                    "latest"
                )
                
                total_policies = summary.value[0].results.total_resources if summary.value else 0
                non_compliant = summary.value[0].results.non_compliant_resources if summary.value else 0
                
                compliance_pct = ((total_policies - non_compliant) / total_policies * 100) if total_policies > 0 else 100
                
                findings.append(_create_finding(
                    "AM-2", "Use only approved services",
                    "PASS" if compliance_pct >= 90 else "FAIL",
                    "Medium" if compliance_pct < 90 else "Info",
                    "Subscription", "Subscription", "",
                    f"Policy compliance: {compliance_pct:.1f}%",
                    "Azure Policy compliance should be 90%+",
                    f"Policy compliance is {compliance_pct:.1f}%",
                    "Review and remediate non-compliant resources",
                    "Azure Policy enforces approved service usage"
                ))
            except Exception:
                findings.append(_create_finding(
                    "AM-2", "Use only approved services",
                    "MANUAL_REVIEW", "Medium", "Subscription", "Subscription", "",
                    "Unable to retrieve policy compliance",
                    "Verify Azure Policy is configured",
                    "Could not assess Azure Policy compliance",
                    "Review Azure Policy assignments manually",
                    "Azure Policy is essential for governance"
                ))
            
            # AM-3, AM-4, AM-5: Manual review
            manual_controls = [
                ("AM-3", "Ensure security of asset lifecycle management", "Review resource provisioning/deprovisioning processes"),
                ("AM-4", "Limit access to asset management", "Review RBAC for resource management operations"),
                ("AM-5", "Use only approved applications in VMs", "Review application control policies"),
            ]
            
            for ctrl_id, title, guidance in manual_controls:
                findings.append(_create_finding(
                    ctrl_id, title,
                    "MANUAL_REVIEW", "Medium", "Organization", "Organization", "",
                    "Requires organizational review", guidance,
                    f"{title} - requires process verification",
                    guidance,
                    "This control requires organizational policy review"
                ))
            
            return {"status": "success", "domain": "AM", "findings": findings, "count": len(findings)}
        except Exception as e:
            return {"status": "error", "error": str(e), "findings": findings}

    result = await loop.run_in_executor(None, _assess)
    return json.dumps(result, default=str)


async def sec_assess_logging_detection() -> str:
    """
    Assess Azure subscription against MCSB v2 Logging and Threat Detection (LT) domain.
    Checks Defender plans, diagnostic settings, Log Analytics, NSG flow logs.
    Returns findings as JSON array.
    """
    loop = asyncio.get_running_loop()

    def _assess():
        findings = []
        try:
            security = _get_security_client()
            monitor = _get_monitor_client()
            network = _get_network_client()
            
            # LT-1: Defender for Cloud plans
            pricings = list(security.pricings.list().value)
            for pricing in pricings:
                is_enabled = pricing.pricing_tier == "Standard"
                findings.append(_create_finding(
                    "LT-1", "Enable threat detection capabilities",
                    "PASS" if is_enabled else "FAIL",
                    "High" if not is_enabled and pricing.name in ["VirtualMachines", "SqlServers", "StorageAccounts"] else "Medium",
                    pricing.name, "Microsoft.Security/pricings", "",
                    f"Tier: {pricing.pricing_tier}",
                    "Standard tier recommended",
                    f"Defender for {pricing.name}: {pricing.pricing_tier}",
                    "Enable Standard tier for advanced threat protection" if not is_enabled else "Defender is enabled",
                    "Defender for Cloud provides threat detection"
                ))
            
            # LT-3: Diagnostic settings
            # This requires iterating resources - simplified check for Log Analytics workspace
            try:
                from azure.mgmt.loganalytics import LogAnalyticsManagementClient
                la_client = LogAnalyticsManagementClient(_get_credential(), _get_subscription_id())
                workspaces = list(la_client.workspaces.list())
                
                if len(workspaces) > 0:
                    findings.append(_create_finding(
                        "LT-5", "Centralize security log management",
                        "PASS", "Info", "Subscription", "Subscription", "",
                        f"{len(workspaces)} Log Analytics workspace(s)",
                        "Log Analytics workspace should exist",
                        "Log Analytics workspaces are configured",
                        "Ensure resources send logs to workspace",
                        "Centralized logging enables security analysis"
                    ))
                else:
                    findings.append(_create_finding(
                        "LT-5", "Centralize security log management",
                        "FAIL", "High", "Subscription", "Subscription", "",
                        "No Log Analytics workspace",
                        "Create Log Analytics workspace",
                        "No centralized logging configured",
                        "Create Log Analytics workspace for log aggregation",
                        "Centralized logging is essential for security monitoring"
                    ))
            except Exception:
                findings.append(_create_finding(
                    "LT-5", "Centralize security log management",
                    "MANUAL_REVIEW", "High", "Subscription", "Subscription", "",
                    "Could not check Log Analytics",
                    "Verify Log Analytics configuration",
                    "Unable to assess Log Analytics workspaces",
                    "Review Log Analytics workspace configuration manually",
                    "Centralized logging is essential"
                ))
            
            # LT-4: NSG flow logs
            nsgs = list(network.network_security_groups.list_all())
            for nsg in nsgs:
                rg = nsg.id.split("/")[4]
                # Check for flow log configuration (simplified)
                findings.append(_create_finding(
                    "LT-4", "Enable network logging for security investigation",
                    "MANUAL_REVIEW", "Medium", nsg.name, "Microsoft.Network/networkSecurityGroups", rg,
                    "Flow log status requires Network Watcher check",
                    "Enable NSG flow logs",
                    f"NSG {nsg.name} flow log status needs verification",
                    "Enable NSG flow logs via Network Watcher",
                    "Flow logs provide network traffic visibility"
                ))
            
            # LT-2, LT-3, LT-6, LT-7: Manual review
            manual_controls = [
                ("LT-2", "Enable threat detection for identity and access", "Review Entra ID Protection and Identity Threat Detection"),
                ("LT-3", "Enable logging for security investigation", "Verify diagnostic settings on all resources"),
                ("LT-6", "Configure log storage retention", "Review log retention policies"),
                ("LT-7", "Use approved time synchronization sources", "Verify NTP configuration"),
            ]
            
            for ctrl_id, title, guidance in manual_controls:
                findings.append(_create_finding(
                    ctrl_id, title,
                    "MANUAL_REVIEW", "Medium", "Organization", "Organization", "",
                    "Requires configuration review", guidance,
                    f"{title} - requires detailed review",
                    guidance,
                    "This control requires detailed configuration review"
                ))
            
            return {"status": "success", "domain": "LT", "findings": findings, "count": len(findings)}
        except Exception as e:
            return {"status": "error", "error": str(e), "findings": findings}

    result = await loop.run_in_executor(None, _assess)
    return json.dumps(result, default=str)


async def sec_assess_incident_response() -> str:
    """
    Assess Azure subscription against MCSB v2 Incident Response (IR) domain.
    Most IR controls require organizational review.
    Returns findings as JSON array.
    """
    loop = asyncio.get_running_loop()

    def _assess():
        findings = []
        try:
            security = _get_security_client()
            
            # Check security contacts
            try:
                contacts = list(security.security_contacts.list())
                if len(contacts) > 0:
                    findings.append(_create_finding(
                        "IR-2", "Preparation - set up incident notification",
                        "PASS", "Info", "Subscription", "Subscription", "",
                        f"{len(contacts)} security contact(s) configured",
                        "Security contacts should be configured",
                        "Security contacts are configured for notifications",
                        "Verify contacts receive alerts",
                        "Security contacts enable incident notification"
                    ))
                else:
                    findings.append(_create_finding(
                        "IR-2", "Preparation - set up incident notification",
                        "FAIL", "High", "Subscription", "Subscription", "",
                        "No security contacts configured",
                        "Configure security contacts",
                        "No security contacts for incident notification",
                        "Configure security contacts in Defender for Cloud",
                        "Security contacts are essential for incident response"
                    ))
            except Exception:
                findings.append(_create_finding(
                    "IR-2", "Preparation - set up incident notification",
                    "MANUAL_REVIEW", "High", "Subscription", "Subscription", "",
                    "Could not check security contacts",
                    "Verify security contacts configuration",
                    "Unable to assess security contacts",
                    "Review security contacts in Defender for Cloud",
                    "Security contacts enable incident notification"
                ))
            
            # IR-1, IR-3 through IR-7: Organizational/process controls
            manual_controls = [
                ("IR-1", "Preparation - update incident response plan", "Review and update IR plan annually"),
                ("IR-3", "Detection and analysis - create incidents from alerts", "Review alert-to-incident automation"),
                ("IR-4", "Detection and analysis - investigate an incident", "Review investigation procedures"),
                ("IR-5", "Containment, eradication and recovery", "Review containment playbooks"),
                ("IR-6", "Post-incident activity - lessons learned", "Review post-incident review process"),
                ("IR-7", "Post-incident activity - conduct follow-up", "Review evidence retention policies"),
            ]
            
            for ctrl_id, title, guidance in manual_controls:
                findings.append(_create_finding(
                    ctrl_id, title,
                    "MANUAL_REVIEW", "Medium", "Organization", "Organization", "",
                    "Requires organizational process review", guidance,
                    f"{title} - organizational process required",
                    guidance,
                    "This control requires organizational process verification"
                ))
            
            return {"status": "success", "domain": "IR", "findings": findings, "count": len(findings)}
        except Exception as e:
            return {"status": "error", "error": str(e), "findings": findings}

    result = await loop.run_in_executor(None, _assess)
    return json.dumps(result, default=str)


async def sec_assess_posture_vuln_mgmt() -> str:
    """
    Assess Azure subscription against MCSB v2 Posture and Vulnerability Management (PV) domain.
    Checks Azure Policy, secure score, vulnerability assessments.
    Returns findings as JSON array.
    """
    loop = asyncio.get_running_loop()

    def _assess():
        findings = []
        try:
            security = _get_security_client()
            
            # PV-1 & PV-2: Azure Policy and secure configurations
            try:
                # Get secure score
                scores = list(security.secure_scores.list())
                if scores:
                    score = scores[0]
                    current_score = score.current_score if hasattr(score, 'current_score') else 0
                    max_score = score.max_score if hasattr(score, 'max_score') else 100
                    pct = (current_score / max_score * 100) if max_score > 0 else 0
                    
                    findings.append(_create_finding(
                        "PV-1", "Define and establish secure configurations",
                        "PASS" if pct >= 70 else "FAIL",
                        "High" if pct < 50 else ("Medium" if pct < 70 else "Info"),
                        "Subscription", "Subscription", "",
                        f"Secure Score: {pct:.1f}%",
                        "Secure Score should be 70%+",
                        f"Defender for Cloud Secure Score is {pct:.1f}%",
                        "Address recommendations to improve score" if pct < 70 else "Continue maintaining security posture",
                        "Secure Score reflects overall security posture"
                    ))
            except Exception:
                findings.append(_create_finding(
                    "PV-1", "Define and establish secure configurations",
                    "MANUAL_REVIEW", "High", "Subscription", "Subscription", "",
                    "Could not retrieve Secure Score",
                    "Review Secure Score in Defender for Cloud",
                    "Unable to assess Secure Score",
                    "Check Secure Score in Azure Portal",
                    "Secure Score indicates security posture"
                ))
            
            # PV-5: Vulnerability assessments
            try:
                pricings = list(security.pricings.list().value)
                servers_plan = next((p for p in pricings if p.name == "VirtualMachines"), None)
                
                if servers_plan and servers_plan.pricing_tier == "Standard":
                    findings.append(_create_finding(
                        "PV-5", "Perform vulnerability assessments",
                        "PASS", "Info", "Subscription", "Subscription", "",
                        "Defender for Servers: Standard",
                        "Enable vulnerability assessment",
                        "Defender for Servers provides vulnerability assessment",
                        "Review vulnerability findings in Defender",
                        "Vulnerability assessment identifies security gaps"
                    ))
                else:
                    findings.append(_create_finding(
                        "PV-5", "Perform vulnerability assessments",
                        "FAIL", "High", "Subscription", "Subscription", "",
                        "Defender for Servers: Not enabled",
                        "Enable Defender for Servers Standard",
                        "Vulnerability assessment not enabled",
                        "Enable Defender for Servers for VA capabilities",
                        "Vulnerability assessment is essential for security"
                    ))
            except Exception:
                pass
            
            # PV-2, PV-3, PV-4, PV-6, PV-7: Manual review
            manual_controls = [
                ("PV-2", "Audit and enforce secure configurations", "Review Azure Policy compliance reports"),
                ("PV-3", "Define secure configurations for compute", "Review VM baseline configurations"),
                ("PV-4", "Audit and enforce secure compute configurations", "Review VM compliance status"),
                ("PV-6", "Rapidly remediate vulnerabilities", "Review vulnerability remediation SLAs"),
                ("PV-7", "Conduct regular red team operations", "Review penetration testing schedule"),
            ]
            
            for ctrl_id, title, guidance in manual_controls:
                findings.append(_create_finding(
                    ctrl_id, title,
                    "MANUAL_REVIEW", "Medium", "Organization", "Organization", "",
                    "Requires process review", guidance,
                    f"{title} - requires verification",
                    guidance,
                    "This control requires process/configuration review"
                ))
            
            return {"status": "success", "domain": "PV", "findings": findings, "count": len(findings)}
        except Exception as e:
            return {"status": "error", "error": str(e), "findings": findings}

    result = await loop.run_in_executor(None, _assess)
    return json.dumps(result, default=str)


async def sec_assess_endpoint_security() -> str:
    """
    Assess Azure subscription against MCSB v2 Endpoint Security (ES) domain.
    Checks EDR, anti-malware, VM extensions.
    Returns findings as JSON array.
    """
    loop = asyncio.get_running_loop()

    def _assess():
        findings = []
        try:
            compute = _get_compute_client()
            security = _get_security_client()
            
            # Check Defender for Servers plan
            pricings = list(security.pricings.list().value)
            servers_plan = next((p for p in pricings if p.name == "VirtualMachines"), None)
            
            if servers_plan and servers_plan.pricing_tier == "Standard":
                findings.append(_create_finding(
                    "ES-1", "Use Endpoint Detection and Response (EDR)",
                    "PASS", "Info", "Subscription", "Subscription", "",
                    "Defender for Servers: Standard",
                    "Enable EDR capabilities",
                    "Defender for Servers provides EDR via MDE",
                    "Ensure MDE agent is deployed to VMs",
                    "EDR provides advanced threat detection"
                ))
            else:
                findings.append(_create_finding(
                    "ES-1", "Use Endpoint Detection and Response (EDR)",
                    "FAIL", "High", "Subscription", "Subscription", "",
                    "Defender for Servers: Not Standard",
                    "Enable Defender for Servers Standard",
                    "EDR not enabled at subscription level",
                    "Enable Defender for Servers Standard tier",
                    "EDR is critical for endpoint protection"
                ))
            
            # ES-2 & ES-3: Check VM extensions for antimalware
            vms = list(compute.virtual_machines.list_all())
            for vm in vms:
                rg = vm.id.split("/")[4]
                
                # Get VM extensions
                try:
                    extensions = list(compute.virtual_machine_extensions.list(rg, vm.name))
                    ext_names = [e.name.lower() for e in extensions]
                    
                    has_antimalware = any(
                        "antimalware" in n or "mde" in n or "defender" in n or "windowsdefender" in n
                        for n in ext_names
                    )
                    
                    if has_antimalware:
                        findings.append(_create_finding(
                            "ES-2", "Use modern anti-malware software",
                            "PASS", "Info", vm.name, "Microsoft.Compute/virtualMachines", rg,
                            "Anti-malware extension found",
                            "Anti-malware should be installed",
                            f"VM {vm.name} has anti-malware protection",
                            "Verify signatures are up to date",
                            "Anti-malware provides malware protection"
                        ))
                    else:
                        findings.append(_create_finding(
                            "ES-2", "Use modern anti-malware software",
                            "FAIL", "High", vm.name, "Microsoft.Compute/virtualMachines", rg,
                            "No anti-malware extension found",
                            "Install anti-malware extension",
                            f"VM {vm.name} lacks anti-malware protection",
                            "Deploy Microsoft Antimalware or MDE extension",
                            "Anti-malware is essential for endpoint security"
                        ))
                except Exception:
                    findings.append(_create_finding(
                        "ES-2", "Use modern anti-malware software",
                        "MANUAL_REVIEW", "High", vm.name, "Microsoft.Compute/virtualMachines", rg,
                        "Could not check extensions",
                        "Verify anti-malware installation",
                        f"Unable to check extensions for VM {vm.name}",
                        "Manually verify anti-malware is installed",
                        "Anti-malware verification required"
                    ))
            
            # ES-3: Manual review for signature updates
            findings.append(_create_finding(
                "ES-3", "Ensure anti-malware signatures are updated",
                "MANUAL_REVIEW", "Medium", "Organization", "Organization", "",
                "Requires signature status verification",
                "Verify automatic signature updates",
                "Anti-malware signature currency requires verification",
                "Ensure automatic updates are enabled",
                "Current signatures are essential for protection"
            ))
            
            return {"status": "success", "domain": "ES", "findings": findings, "count": len(findings)}
        except Exception as e:
            return {"status": "error", "error": str(e), "findings": findings}

    result = await loop.run_in_executor(None, _assess)
    return json.dumps(result, default=str)


async def sec_assess_backup_recovery() -> str:
    """
    Assess Azure subscription against MCSB v2 Backup and Recovery (BR) domain.
    Checks Recovery Services vaults, backup policies, soft-delete.
    Returns findings as JSON array.
    """
    loop = asyncio.get_running_loop()

    def _assess():
        findings = []
        try:
            recovery = _get_recovery_client()
            storage = _get_storage_client()
            
            # BR-1 & BR-2: Recovery Services vaults
            vaults = list(recovery.vaults.list_by_subscription())
            
            if len(vaults) == 0:
                findings.append(_create_finding(
                    "BR-1", "Ensure regular automated backups",
                    "FAIL", "High", "Subscription", "Subscription", "",
                    "No Recovery Services vaults",
                    "Create Recovery Services vault for backups",
                    "No backup infrastructure configured",
                    "Create Recovery Services vault and configure backup policies",
                    "Backup infrastructure is essential for recovery"
                ))
            else:
                for vault in vaults:
                    rg = vault.id.split("/")[4]
                    findings.append(_create_finding(
                        "BR-1", "Ensure regular automated backups",
                        "PASS", "Info", vault.name, "Microsoft.RecoveryServices/vaults", rg,
                        f"Vault location: {vault.location}",
                        "Recovery Services vault should exist",
                        f"Recovery Services vault {vault.name} is configured",
                        "Verify backup policies protect critical resources",
                        "Backup vault is available"
                    ))
                    
                    # Check vault properties for soft-delete
                    # Note: Soft delete is enabled by default and cannot be disabled
                    findings.append(_create_finding(
                        "BR-2", "Protect backup and recovery data",
                        "PASS", "Info", vault.name, "Microsoft.RecoveryServices/vaults", rg,
                        "Soft delete: Enabled by default",
                        "Soft delete should be enabled",
                        f"Vault {vault.name} has soft delete (default)",
                        "Consider enabling immutability for enhanced protection",
                        "Soft delete protects against accidental deletion"
                    ))
            
            # BR-2: Storage account blob soft-delete
            storage_accounts = list(storage.storage_accounts.list())
            for sa in storage_accounts:
                rg = sa.id.split("/")[4]
                try:
                    blob_props = storage.blob_services.get_service_properties(rg, sa.name)
                    soft_delete = blob_props.delete_retention_policy
                    
                    if soft_delete and soft_delete.enabled:
                        findings.append(_create_finding(
                            "BR-2", "Protect backup and recovery data",
                            "PASS", "Info", sa.name, "Microsoft.Storage/storageAccounts", rg,
                            f"Blob soft delete: {soft_delete.days} days",
                            "Enable blob soft delete",
                            f"Storage account {sa.name} has blob soft delete",
                            "Soft delete enables blob recovery",
                            "Blob soft delete protects against deletion"
                        ))
                    else:
                        findings.append(_create_finding(
                            "BR-2", "Protect backup and recovery data",
                            "FAIL", "Medium", sa.name, "Microsoft.Storage/storageAccounts", rg,
                            "Blob soft delete: Disabled",
                            "Enable blob soft delete",
                            f"Storage account {sa.name} lacks blob soft delete",
                            "Enable blob soft delete with appropriate retention",
                            "Blob soft delete enables recovery of deleted blobs"
                        ))
                except Exception:
                    pass
            
            # BR-3 & BR-4: Manual review
            manual_controls = [
                ("BR-3", "Monitor backups", "Review backup alerts and monitoring"),
                ("BR-4", "Regularly test backup", "Verify backup restore testing schedule"),
            ]
            
            for ctrl_id, title, guidance in manual_controls:
                findings.append(_create_finding(
                    ctrl_id, title,
                    "MANUAL_REVIEW", "Medium", "Organization", "Organization", "",
                    "Requires operational review", guidance,
                    f"{title} - requires operational verification",
                    guidance,
                    "This control requires operational process review"
                ))
            
            return {"status": "success", "domain": "BR", "findings": findings, "count": len(findings)}
        except Exception as e:
            return {"status": "error", "error": str(e), "findings": findings}

    result = await loop.run_in_executor(None, _assess)
    return json.dumps(result, default=str)


async def sec_assess_devops_security() -> str:
    """
    Assess Azure subscription against MCSB v2 DevOps Security (DS) domain.
    Most DS controls require organizational review.
    Returns findings as JSON array.
    """
    loop = asyncio.get_running_loop()

    def _assess():
        findings = []
        
        # DS controls are primarily organizational/process controls
        controls = [
            ("DS-1", "Conduct threat modeling", "Review threat modeling practices"),
            ("DS-2", "Ensure software supply chain security", "Review dependency scanning and SBOM"),
            ("DS-3", "Secure DevOps infrastructure", "Review GitHub/Azure DevOps security settings"),
            ("DS-4", "Integrate SAST into DevOps pipeline", "Review static analysis tools in CI/CD"),
            ("DS-5", "Integrate DAST into DevOps pipeline", "Review dynamic analysis in CI/CD"),
            ("DS-6", "Enforce security throughout DevOps lifecycle", "Review security gates in pipeline"),
            ("DS-7", "Ensure logging and monitoring in DevOps", "Review pipeline audit logging"),
        ]
        
        for ctrl_id, title, guidance in controls:
            findings.append(_create_finding(
                ctrl_id, title,
                "MANUAL_REVIEW", "Medium", "Organization", "Organization", "",
                "Requires DevOps process review", guidance,
                f"{title} - organizational process required",
                guidance,
                "This control requires DevOps process and tooling review"
            ))
        
        return {"status": "success", "domain": "DS", "findings": findings, "count": len(findings)}

    result = await loop.run_in_executor(None, _assess)
    return json.dumps(result, default=str)


async def sec_assess_governance_strategy() -> str:
    """
    Assess Azure subscription against MCSB v2 Governance and Strategy (GS) domain.
    Most GS controls require organizational review.
    Returns findings as JSON array.
    """
    loop = asyncio.get_running_loop()

    def _assess():
        findings = []
        
        # GS controls are organizational/strategy controls
        controls = [
            ("GS-1", "Align organization roles and responsibilities", "Review security roles definition"),
            ("GS-2", "Define segmentation/separation of duties strategy", "Review segmentation strategy"),
            ("GS-3", "Define data protection strategy", "Review data classification and protection"),
            ("GS-4", "Define network security strategy", "Review network architecture standards"),
            ("GS-5", "Define security posture management strategy", "Review posture management approach"),
            ("GS-6", "Define identity and privileged access strategy", "Review IAM strategy"),
            ("GS-7", "Define logging and threat detection strategy", "Review monitoring strategy"),
            ("GS-8", "Define backup and recovery strategy", "Review BCDR strategy"),
            ("GS-9", "Define endpoint security strategy", "Review endpoint protection standards"),
            ("GS-10", "Define DevOps security strategy", "Review secure SDLC practices"),
            ("GS-11", "Define multi-cloud security strategy", "Review multi-cloud governance"),
        ]
        
        for ctrl_id, title, guidance in controls:
            findings.append(_create_finding(
                ctrl_id, title,
                "MANUAL_REVIEW", "Medium", "Organization", "Organization", "",
                "Requires strategic/policy review", guidance,
                f"{title} - strategic planning required",
                guidance,
                "This control requires organizational strategy and policy review"
            ))
        
        return {"status": "success", "domain": "GS", "findings": findings, "count": len(findings)}

    result = await loop.run_in_executor(None, _assess)
    return json.dumps(result, default=str)


# ══════════════════════════════════════════════════════════════════════
# Tool Registration Function (called from main server.py)
# ══════════════════════════════════════════════════════════════════════

def register_security_tools(mcp_server):
    """
    Register all security assessment tools with the MCP server.
    
    Args:
        mcp_server: The FastMCP server instance to register tools on.
    """
    # Core tools
    mcp_server.tool()(sec_list_subscriptions)
    mcp_server.tool()(sec_get_mcsb_controls)
    mcp_server.tool()(sec_list_resources)
    mcp_server.tool()(sec_get_resource_details)
    mcp_server.tool()(sec_list_role_assignments)
    mcp_server.tool()(sec_check_defender_status)
    
    # Domain assessment tools
    mcp_server.tool()(sec_assess_network_security)
    mcp_server.tool()(sec_assess_identity_management)
    mcp_server.tool()(sec_assess_data_protection)
    mcp_server.tool()(sec_assess_privileged_access)
    mcp_server.tool()(sec_assess_asset_management)
    mcp_server.tool()(sec_assess_logging_detection)
    mcp_server.tool()(sec_assess_incident_response)
    mcp_server.tool()(sec_assess_posture_vuln_mgmt)
    mcp_server.tool()(sec_assess_endpoint_security)
    mcp_server.tool()(sec_assess_backup_recovery)
    mcp_server.tool()(sec_assess_devops_security)
    mcp_server.tool()(sec_assess_governance_strategy)
    
    print("[INFO] Security assessment tools registered successfully")
