"""
Invoke tasks for managing application secrets in AWS Secrets Manager.

Environments map to these secret IDs (eu-central-1 by default):
 - prod:    backend/prod/product-api/managed, backend/prod/product-api/manual
 - staging: backend/staging/product-api/managed, backend/staging/product-api/manual
 - preview: backend/staging/product-api/managed, backend/staging/product-api/manual,
            backend/staging-preview/product-api

These tasks are thin wrappers around boto3 to help you:
 - show:   View secrets (merged or per-secret)
 - add:    Upsert a single key into the "manual" secret for the env
 - verify: Check a key exists (and optionally matches an expected value)

Usage examples:
  inv secrets.show --env=prod                # merged view (manual overrides managed)
  inv secrets.show --env=staging --raw       # show each backing secret separately
  inv secrets.add --env=prod --key=FOO --value=bar
  inv secrets.verify --env=preview --key=RETURNS_RECAPTCHA_SITE_KEY

Pass AWS profile/region if needed:
  inv secrets.show --env=prod --profile=prod --region=eu-central-1
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

import boto3
from botocore.exceptions import ClientError
import invoke


DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-central-1")


def _secret_ids_for_env(env: str) -> List[str]:
    e = env.strip().lower()
    if e in {"prod", "production"}:
        return [
            "backend/prod/product-api/managed",
            "backend/prod/product-api/manual",
        ]
    if e in {"staging", "stage"}:
        return [
            "backend/staging/product-api/managed",
            "backend/staging/product-api/manual",
        ]
    if e in {"preview", "pr", "previews"}:
        return [
            "backend/staging/product-api/managed",
            "backend/staging/product-api/manual",
            "backend/staging-preview/product-api",
        ]
    raise ValueError(f"Unknown env '{env}'. Use one of: prod, staging, preview")


def _boto_session(profile: str | None, region: str | None):
    params: Dict[str, Any] = {}
    if profile:
        params["profile_name"] = profile
    return boto3.session.Session(**params), (region or DEFAULT_REGION)


def _get_secret_json(sess: boto3.session.Session, region: str, secret_id: str) -> Tuple[Dict[str, Any], str]:
    sm = sess.client("secretsmanager", region_name=region)
    try:
        resp = sm.get_secret_value(SecretId=secret_id)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
            return {}, ""
        raise
    secret = resp.get("SecretString") or ""
    if not secret:
        return {}, resp.get("VersionId", "")
    try:
        data = json.loads(secret)
    except json.JSONDecodeError:
        # Store as a single-value mapping under "value" if plaintext was used by mistake
        data = {"value": secret}
    return data, resp.get("VersionId", "")


def _put_secret_json(sess: boto3.session.Session, region: str, secret_id: str, payload: Dict[str, Any]) -> str:
    sm = sess.client("secretsmanager", region_name=region)
    resp = sm.put_secret_value(SecretId=secret_id, SecretString=json.dumps(payload))
    return resp.get("VersionId", "")


def _merge_dicts(dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for d in dicts:
        out.update(d or {})
    return out


def _redact(value: Any) -> str:
    s = str(value)
    if len(s) <= 8:
        return "***"
    return f"{s[:4]}…{s[-4:]}"  # keep small context for visual diff


@invoke.task
def show(
    ctx,
    env: str = "prod",
    profile: str | None = None,
    region: str | None = None,
    raw: bool = False,
    redact: bool = True,
):
    """Show secrets for an environment.

    By default prints a merged view (later secrets override earlier ones).
    Use --raw to print each backing secret separately.
    """
    sess, reg = _boto_session(profile, region)
    ids = _secret_ids_for_env(env)
    parts: List[Tuple[str, Dict[str, Any]]] = []
    for sid in ids:
        data, _ = _get_secret_json(sess, reg, sid)
        parts.append((sid, data))

    if raw:
        for sid, data in parts:
            print(f"# {sid}")
            items = sorted(data.items())
            for k, v in items:
                print(f"{k}={( _redact(v) if redact else v )}")
            print()
    else:
        merged = _merge_dicts([d for _, d in parts])
        for k, v in sorted(merged.items()):
            print(f"{k}={( _redact(v) if redact else v )}")


@invoke.task
def add(
    ctx,
    env: str,
    key: str,
    value: str,
    profile: str | None = None,
    region: str | None = None,
    secret: str = "manual",
):
    """Add or update a key in the env's manual secret (default).

    Set --secret=managed to target the managed secret (not recommended).
    """
    sess, reg = _boto_session(profile, region)
    ids = _secret_ids_for_env(env)
    target_id: str
    match secret:
        case "manual":
            target_id = next(s for s in ids if s.endswith("/manual"))
        case "managed":
            target_id = next(s for s in ids if s.endswith("/managed"))
        case _:
            raise ValueError("--secret must be 'manual' or 'managed'")

    data, _ = _get_secret_json(sess, reg, target_id)
    before = data.get(key)
    data[key] = value
    ver = _put_secret_json(sess, reg, target_id, data)
    print(f"Updated {target_id} version={ver} key={key} from={_redact(before)} to={_redact(value)}")


@invoke.task
def verify(
    ctx,
    env: str,
    key: str,
    expect: str | None = None,
    profile: str | None = None,
    region: str | None = None,
):
    """Verify a key exists in the merged view (managed → manual → preview overlay).

    Optionally assert its value with --expect.
    """
    sess, reg = _boto_session(profile, region)
    ids = _secret_ids_for_env(env)
    parts: List[Dict[str, Any]] = []
    for sid in ids:
        data, _ = _get_secret_json(sess, reg, sid)
        parts.append(data)
    merged = _merge_dicts(parts)

    if key not in merged:
        raise SystemExit(f"Key '{key}' not found in env '{env}'")
    val = merged[key]
    print(f"Found {key}={_redact(val)} in env={env}")
    if expect is not None:
        if str(val) == expect:
            print("Value matches --expect ✔")
        else:
            raise SystemExit("Value does not match --expect ✘")

