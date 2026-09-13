from __future__ import annotations

import base64
import json


def _load_boto3():
    try:
        import boto3  # type: ignore
    except (
        ModuleNotFoundError
    ) as exc:  # pragma: no cover - only hit in local environments
        raise RuntimeError(
            "boto3 is required at runtime. Deploy this code in Lambda or install boto3 locally."
        ) from exc
    return boto3


def get_secret_token(secret_name: str) -> str:
    boto3 = _load_boto3()
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)

    if "SecretString" in response:
        secret_value = response["SecretString"]
    else:
        secret_value = base64.b64decode(response["SecretBinary"]).decode("utf-8")

    try:
        parsed = json.loads(secret_value)
    except json.JSONDecodeError:
        return secret_value.strip()

    for key in ("token", "github_token", "access_token"):
        if key in parsed:
            return str(parsed[key]).strip()

    raise ValueError(
        "Secrets Manager payload must be a plain token or JSON containing a token key."
    )


def get_dynamodb_table(table_name: str):
    boto3 = _load_boto3()
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)
