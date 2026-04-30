# Azure Networking Fix for SAOS API Access

## Problem Statement
The OmniFlowCentral Function App deployed on **FlexConsumption plan** in Switzerland North cannot reach the external SAOS API (`www.saos.org.pl`).

### Error Details
```
HTTPSConnectionPool(host='www.saos.org.pl', port=443): Max retries exceeded
[Errno 101] Network is unreachable
```

### Root Cause
FlexConsumption tier uses a **shared, dynamic outbound IP pool**. The SAOS API may:
- Have firewall rules blocking shared cloud IP ranges
- Experience routing issues with ephemeral IPs from consumption plans
- Rate-limit or block requests from non-whitelisted sources

## Verification

### Local Testing (✅ Works)
```bash
curl "https://www.saos.org.pl/api/search/judgments?pageSize=10&pageNumber=0&all=konstytucja"
# Returns 200 OK with judgment results
```

### Azure Backend Testing (❌ Fails)
```python
POST https://omniflowcentral.azurewebsites.net/api/tools/call
payload: {"tool": "saos_search", "payload": {"q": "konstytucja"}}
# Response: 502 UPSTREAM_ERROR - Network is unreachable
```

## Recommended Solutions (Priority Order)

### 1. ⭐ **Upgrade App Service Plan to Standard/Premium** (Lowest effort)

**Advantages:**
- Static, reserved outbound IPs
- Better control over network egress
- More predictable performance
- Can be whitelisted with SAOS

**Steps:**
```bash
# Change pricing tier
az appservice plan update \
  --name ASP-AgentResourceGroup-972d \
  --resource-group AgentResourceGroup \
  --sku S1  # or P1V2 for higher throughput

# Function App automatically uses new plan without re-deployment
# Verify new outbound IPs
az functionapp show \
  --name OmniFlowCentral \
  --resource-group AgentResourceGroup \
  --query "outboundIpAddresses" -o json
```

**Cost Impact:** ~$80-400/month (vs ~$0.20/execution on Flex)

---

### 2. **Use Azure NAT Gateway** (Recommended if staying on Flex)

**Prerequisites:**
- VNet with NAT Gateway
- Standard SKU Public IP
- Route association

**Steps:**
```bash
# Create NAT Gateway in Switzerland North
az network nat gateway create \
  --resource-group AgentResourceGroup \
  --name omniflow-nat \
  --location switzerlandnorth \
  --public-ip-address-ids <pip_id> \
  --idle-timeout 4

# Associate with Function App VNet subnet
# (Requires Function App migration to VNet, see step 4)
```

---

### 3. **Azure API Management (API Gateway Proxy)**

**Concept:** Use APIM as a middleware proxy to SAOS API.

**Advantages:**
- Can add caching to reduce SAOS calls
- Request/response transformation
- Rate limiting and throttling
- IP allowlisting at APIM gateway

**Setup:**
```bash
# Create APIM instance
az apim create \
  --name omniflow-apim \
  --resource-group AgentResourceGroup \
  --publisher-name "OmniFlow" \
  --publisher-email admin@omniflow.local

# Add SAOS API backend
# Configure policies for header/auth handling
```

**Cost:** ~$40-400/month

---

### 4. **VNet Integration + NAT Gateway** (Most control)

**Highest effort but most reliable long-term solution.**

**Steps:**
1. Create VNet in Switzerland North
2. Create NAT Gateway with Static Public IP
3. Integrate Function App with VNet
4. Route outbound traffic through NAT

```bash
# Create VNet
az network vnet create \
  --name omniflow-vnet \
  --resource-group AgentResourceGroup \
  --address-prefix 10.0.0.0/16 \
  --subnet-name functions \
  --subnet-prefix 10.0.1.0/24

# Create Public IP for NAT
az network public-ip create \
  --resource-group AgentResourceGroup \
  --name omniflow-nat-ip \
  --sku Standard \
  --location switzerlandnorth

# Create NAT Gateway
az network nat gateway create \
  --resource-group AgentResourceGroup \
  --name omniflow-nat \
  --public-ip-addresses omniflow-nat-ip \
  --idle-timeout 4

# Associate NAT with subnet
az network vnet subnet update \
  --resource-group AgentResourceGroup \
  --vnet-name omniflow-vnet \
  --name functions \
  --nat-gateway omniflow-nat

# Connect Function App to VNet
az functionapp vnet-integration add \
  --resource-group AgentResourceGroup \
  --name OmniFlowCentral \
  --vnet omniflow-vnet \
  --subnet functions
```

---

## Temporary Workaround: SAOS Response Caching

If migration takes time, implement a caching strategy:

```python
# In saos_api.py
from azure.storage.blob import BlobServiceClient
import hashlib
import json

SAOS_CACHE_PREFIX = "users/public/cache/saos/"

def saos_search_cached(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Try Azure backend (may fail with network error).
    If fails, check cache. If cache hit, return cached result.
    """
    cache_key = hashlib.md5(
        json.dumps(params, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    cache_blob = f"{SAOS_CACHE_PREFIX}searches/{cache_key}.json"
    
    try:
        # Try live API
        return saos_search(params)
    except ToolError as e:
        if "Network is unreachable" in str(e):
            # Fall back to cache
            from .blob_ops import read_blob
            try:
                cached = read_blob(cache_blob, user_id="public")
                return json.loads(cached)
            except Exception:
                raise ToolError("CACHE_MISS", "Live API unreachable and no cached result.")
        raise
```

---

## Testing Checklist

After implementing any solution:

```bash
# 1. Verify outbound IPs changed
az functionapp show \
  --name OmniFlowCentral \
  --resource-group AgentResourceGroup \
  --query outboundIpAddresses

# 2. Test SAOS search from backend
curl -X POST https://omniflowcentral.../api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool":"saos_search","payload":{"q":"konstytucja","limit":5}}'

# 3. Expect 200 with hits
```

---

## Timeline Estimate

| Solution | Implementation | Cost | Reliability |
|----------|--|------|---|
| Upgrade to Standard | 1 hour | Medium | High |
| NAT Gateway | 3-4 hours | Low | High |
| APIM Proxy | 4-6 hours | Medium | Very High |
| VNet + NAT | 6-8 hours | Low | Very High |
| Caching (temp) | 1-2 hours | None | Low (band-aid) |

---

## Recommended Next Steps

1. **Immediate (this week):** 
   - Implement SAOS response caching (workaround)
   - Document current state

2. **Short-term (1-2 weeks):**
   - Upgrade to Standard plan or implement NAT Gateway
   - Test SAOS connectivity from Azure

3. **Long-term:**
   - Evaluate APIM for broader API gateway strategy
   - Consider VNet architecture for production hardening

---

## References

- [Azure Function App VNet Integration](https://docs.microsoft.com/en-us/azure/azure-functions/functions-create-vnet)
- [Azure NAT Gateway](https://docs.microsoft.com/en-us/azure/virtual-network/nat-gateway/nat-overview)
- [FlexConsumption Networking Limits](https://docs.microsoft.com/en-us/azure/azure-functions/flex-consumption-plan)
- [Azure API Management](https://docs.microsoft.com/en-us/azure/api-management/)
