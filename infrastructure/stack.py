import aws_cdk as cdk
from aws_cdk import (
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_certificatemanager as acm,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct

DOMAIN = "lambda-layer-explorer.com"


class LambdaLayersStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── Route 53 hosted zone (created automatically when registering via R53)
        hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone", domain_name=DOMAIN
        )

        # ── ACM certificate (must be in us-east-1 for CloudFront) ────────────
        certificate = acm.Certificate(
            self,
            "Certificate",
            domain_name=DOMAIN,
            subject_alternative_names=[f"www.{DOMAIN}"],
            validation=acm.CertificateValidation.from_dns(hosted_zone),
        )

        # ── S3 bucket (private) ───────────────────────────────────────────────
        bucket = s3.Bucket(
            self,
            "LayersBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ── CloudFront OAC + distribution ────────────────────────────────────
        oac = cloudfront.S3OriginAccessControl(self, "OAC")

        s3_origin = origins.S3BucketOrigin.with_origin_access_control(
            bucket, origin_access_control=oac
        )

        # Cache policy for /data/* — short TTL so weekly updates surface quickly
        data_cache_policy = cloudfront.CachePolicy(
            self,
            "DataCachePolicy",
            default_ttl=Duration.minutes(15),
            min_ttl=Duration.seconds(0),
            max_ttl=Duration.hours(1),
            cookie_behavior=cloudfront.CacheCookieBehavior.none(),
            header_behavior=cloudfront.CacheHeaderBehavior.none(),
            query_string_behavior=cloudfront.CacheQueryStringBehavior.none(),
        )

        distribution = cloudfront.Distribution(
            self,
            "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=s3_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            additional_behaviors={
                "/data/*": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=data_cache_policy,
                )
            },
            domain_names=[DOMAIN, f"www.{DOMAIN}"],
            certificate=certificate,
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
        )

        # ── Route 53: A records → CloudFront ──────────────────────────────────
        cf_target = route53.RecordTarget.from_alias(
            route53_targets.CloudFrontTarget(distribution)
        )
        route53.ARecord(
            self, "ARecord", zone=hosted_zone, target=cf_target
        )
        route53.ARecord(
            self, "WwwARecord", zone=hosted_zone, record_name="www", target=cf_target
        )

        # ── Lambda: Discovery ─────────────────────────────────────────────────
        discovery_fn = lambda_.Function(
            self,
            "DiscoveryFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambdas/discovery"),
            timeout=Duration.minutes(5),
            memory_size=256,
            description="Discovers public AWS-owned Lambda layers for Python runtimes",
        )
        discovery_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "lambda:ListLayers",
                    "lambda:ListLayerVersions",
                    "lambda:GetLayerVersion",
                ],
                resources=["*"],
            )
        )

        # ── Lambda: Inspector ─────────────────────────────────────────────────
        inspector_fn = lambda_.Function(
            self,
            "InspectorFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambdas/inspector"),
            timeout=Duration.minutes(10),
            memory_size=1024,
            ephemeral_storage_size=cdk.Size.mebibytes(2048),
            description="Downloads a layer zip and catalogues its Python packages",
        )
        inspector_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lambda:GetLayerVersion"],
                resources=["*"],
            )
        )

        # ── Lambda: Orchestrator ──────────────────────────────────────────────
        orchestrator_fn = lambda_.Function(
            self,
            "OrchestratorFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambdas/orchestrator"),
            timeout=Duration.minutes(15),
            memory_size=256,
            description="Coordinates discovery → inspection → publish pipeline",
            environment={
                "DATA_BUCKET": bucket.bucket_name,
                "DISCOVERY_FUNCTION_NAME": discovery_fn.function_name,
                "INSPECTOR_FUNCTION_NAME": inspector_fn.function_name,
                "CF_DISTRIBUTION_ID": distribution.distribution_id,
            },
        )
        bucket.grant_put(orchestrator_fn)
        discovery_fn.grant_invoke(orchestrator_fn)
        inspector_fn.grant_invoke(orchestrator_fn)
        orchestrator_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cloudfront:CreateInvalidation"],
                resources=[
                    f"arn:aws:cloudfront::{self.account}:distribution/{distribution.distribution_id}"
                ],
            )
        )

        # ── EventBridge: weekly trigger (Monday 06:00 UTC) ────────────────────
        weekly_rule = events.Rule(
            self,
            "WeeklyRefreshRule",
            schedule=events.Schedule.cron(
                minute="0",
                hour="6",
                week_day="MON",
                month="*",
                year="*",
            ),
            description="Triggers the layer cataloguing pipeline every Monday at 06:00 UTC",
        )
        weekly_rule.add_target(targets.LambdaFunction(orchestrator_fn))

        # ── Deploy React frontend ─────────────────────────────────────────────
        s3deploy.BucketDeployment(
            self,
            "DeployFrontend",
            sources=[s3deploy.Source.asset("frontend/dist")],
            destination_bucket=bucket,
            distribution=distribution,
            distribution_paths=["/*"],
            prune=False,
        )

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(self, "SiteURL", value=f"https://{DOMAIN}")
        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(
            self,
            "OrchestratorFunctionName",
            value=orchestrator_fn.function_name,
            description="Invoke this manually to trigger an immediate refresh",
        )
