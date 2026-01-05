from setuptools import setup, find_packages

setup(
    name="OmniFlowCentral",
    version="0.0.1",
    description="OmniFlowCentral tools and functions package",
    packages=find_packages(exclude=("tests", "docs")),
    include_package_data=True,
)
