"""
Azure Functions deploy shim.

When deploying `OmniFlowCentral/**` as the Function App package root, Python modules live under:
  /home/site/wwwroot/<module>

Many handlers import `OmniFlowCentral.shared.*`. This package provides that namespace and
bridges it to the deployed top-level `shared/*` package.
"""

