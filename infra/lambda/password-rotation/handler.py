"""
Aurora Password Rotation Sync Lambda

When Aurora's ManageMasterUserPassword rotates the DB password automatically,
this Lambda reads the new password from the RDS-managed secret and updates
the application's DATABASE_URL secret in Secrets Manager.

Triggered by: EventBridge rule on Secrets Manager rotation events for the
RDS-managed secret (rds!cluster-*).

Environment variables:
  - RDS_CLUSTER_ID: Aurora cluster identifier (e.g., "tecnoepec-development")
  - APP_SECRET_NAME: Application secret name (e.g., "development.BRANDBRAIN_DATABASE_URL")
  - ECS_CLUSTER: ECS cluster name for service restart (e.g., "main")
  - ECS_SERVICES: Comma-separated ECS service names to restart (e.g., "brandbrain-api,brandbrain-worker")
"""

import json
import logging
import os
from urllib.parse import quote_plus

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

rds = boto3.client("rds")
sm = boto3.client("secretsmanager")
ecs = boto3.client("ecs")


def handler(event, context):
    cluster_id = os.environ["RDS_CLUSTER_ID"]
    app_secret_name = os.environ["APP_SECRET_NAME"]
    ecs_cluster = os.environ.get("ECS_CLUSTER", "main")
    ecs_services = os.environ.get("ECS_SERVICES", "").split(",")

    logger.info("Starting password rotation sync for cluster %s", cluster_id)

    # 1. Get current RDS-managed secret ARN from the cluster
    cluster = rds.describe_db_clusters(DBClusterIdentifier=cluster_id)["DBClusters"][0]
    managed_secret_arn = cluster["MasterUserSecret"]["SecretArn"]
    logger.info("RDS managed secret: %s", managed_secret_arn)

    # 2. Read the current password from the RDS-managed secret
    managed_secret = json.loads(
        sm.get_secret_value(SecretId=managed_secret_arn)["SecretString"]
    )
    username = managed_secret["username"]
    password = managed_secret["password"]
    host = managed_secret["host"]
    port = managed_secret.get("port", 5432)
    dbname = managed_secret.get("dbname", cluster.get("DatabaseName", "brandbrain"))

    # 3. Build the new DATABASE_URL
    encoded_password = quote_plus(password)
    new_url = f"postgresql+psycopg://{username}:{encoded_password}@{host}:{port}/{dbname}?sslmode=require"
    logger.info("Built new DATABASE_URL for host=%s db=%s", host, dbname)

    # 4. Update the application secret
    sm.put_secret_value(SecretId=app_secret_name, SecretString=new_url)
    logger.info("Updated secret %s", app_secret_name)

    # 5. Force new deployment on ECS services to pick up new secret
    restarted = []
    for service_name in ecs_services:
        service_name = service_name.strip()
        if not service_name:
            continue
        try:
            ecs.update_service(
                cluster=ecs_cluster,
                service=service_name,
                forceNewDeployment=True,
            )
            restarted.append(service_name)
            logger.info("Triggered redeployment: %s", service_name)
        except Exception as e:
            logger.error("Failed to restart %s: %s", service_name, e)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Password rotation sync complete",
            "secret_updated": app_secret_name,
            "services_restarted": restarted,
        }),
    }
