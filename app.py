import os
import subprocess

import aws_cdk as cdk
from infrastructure.stack import LambdaLayersStack

# Build the React frontend before CDK synthesis so BucketDeployment
# can simply upload the pre-built dist/ folder (no Docker required).
_frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
_dist_dir = os.path.join(_frontend_dir, "dist")
if not os.path.isdir(_dist_dir):
    print("Building frontend...")
    subprocess.run(["npm", "install"], cwd=_frontend_dir, check=True)
    subprocess.run(["npm", "run", "build"], cwd=_frontend_dir, check=True)

app = cdk.App()

LambdaLayersStack(
    app,
    "LambdaLayersStack",
    env=cdk.Environment(region="us-east-1", account="058264170381"),
)

app.synth()

