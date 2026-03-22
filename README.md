# AWS Lambda Layers Explorer

AWS publishes official Lambda layers — Lambda Powertools, SDK for pandas, OpenTelemetry, and others — but provides no easy way to see what Python packages are actually bundled inside them. This project solves that with a fully serverless pipeline that downloads, inspects, and catalogues every layer weekly, then surfaces the results in a searchable React UI.

**[Live site →](https://d1turspi33srjo.cloudfront.net)**

---

## How it works

A weekly EventBridge rule triggers an orchestration pipeline across three Lambda functions:

1. **Discovery** — probes known AWS-published layer ARNs via `GetLayerVersion` to find the current latest version of each layer
2. **Inspector** — downloads each layer zip, extracts `.dist-info/METADATA` and `.egg-info/PKG-INFO` files, and parses out every bundled Python package
3. **Orchestrator** — coordinates the pipeline, writes the compiled result to S3 as `layers.json`, and invalidates the CloudFront cache

The React frontend fetches that JSON at runtime — no rebuild needed when data updates.

```
EventBridge (weekly)
  → Orchestrator → Discovery → Inspector (×N)
                → S3 (layers.json) → CloudFront → Browser
```

Infrastructure is defined entirely in Python CDK: S3, CloudFront with OAC, three Lambda functions, IAM roles, and the EventBridge schedule.

---

## Interesting problems

**AWS's `ListLayerVersions` API doesn't work cross-account.** Public layers grant `GetLayerVersion` to `*` in their resource policy, but not `ListLayerVersions` — so you can't enumerate a layer's versions from outside the publisher's account. The discovery function works around this with a seed-version probe: each known layer has a recorded version number, and the function uses exponential stepping + binary search to find the true latest version in O(log n) API calls.

**Old layer versions have no public resource policy.** Even `GetLayerVersion` fails on very early versions (v1, v2, ...) of most public layers — AWS didn't add the `*` grant retroactively. Starting a probe at version 1 would silently fail for every layer. The seed-based approach sidesteps this entirely.

**AWS has no public catalogue of vended layers.** The full list of AWS-owned layers is only accessible through a private console API endpoint (`/aws-vended-layers`) that requires session cookies. The layer accounts, naming conventions, and version numbers were sourced by inspecting the console network traffic, then encoded into the discovery function.

---

## Stack

- **Infrastructure** — Python CDK (S3, CloudFront, Lambda, EventBridge, IAM)
- **Backend** — Python 3.12 Lambda functions
- **Frontend** — React, TypeScript, Vite, Material UI
- **Region** — us-east-1
