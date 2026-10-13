import httpx
import yaml

from kestra.constants import _RESERVED_FLOW_IDS


async def _create_flow_from_yaml(client: httpx.AsyncClient, yaml_definition: str) -> dict:
    doc = yaml.safe_load(yaml_definition)
    ns = doc.get("namespace")
    fid = doc.get("id")
    if not ns or not fid:
        raise ValueError("YAML must include 'namespace' and 'id' fields")

    if fid in _RESERVED_FLOW_IDS:
        allowed = ", ".join(sorted(_RESERVED_FLOW_IDS))
        raise ValueError(
            f"The flow ID {fid} is reserved and cannot be used. "
            f"Please choose a different ID (not: {allowed})."
        )

    headers = {"Content-Type": "application/x-yaml"}
    try:
        resp = await client.post("/flows", content=yaml_definition, headers=headers)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code in (409, 422):
            upd = await client.put(
                f"/flows/{ns}/{fid}", content=yaml_definition, headers=headers
            )
            upd.raise_for_status()
            return upd.json()
        raise


async def _create_app(client: httpx.AsyncClient, yaml_source: str) -> dict:
    headers = {"Content-Type": "application/x-yaml"}
    try:
        resp = await client.post("/apps", content=yaml_source, headers=headers)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (409, 422):
            doc = yaml.safe_load(yaml_source)
            app_id = doc.get("id")
            app_namespace = doc.get("namespace")
            app_flow_id = doc.get("flowId")

            if not app_id or not app_namespace:
                raise ValueError(
                    "YAML must include 'id' and 'namespace' fields for update."
                )

            search_resp = await client.get(
                "/apps/search",
                params={
                    "q": app_id,
                    "namespace": app_namespace,
                    "flowId": app_flow_id,
                },
            )
            search_resp.raise_for_status()
            search_results = search_resp.json()

            if not search_results["results"]:
                raise ValueError(
                    f"Could not find existing app with id '{app_id}' in namespace '{app_namespace}'"
                )

            uid_val = search_results["results"][0]["uid"]
            if not uid_val:
                raise ValueError("YAML must include 'uid' field for update.")
            put_resp = await client.put(
                f"/apps/{uid_val}", content=yaml_source, headers=headers
            )
            if put_resp.status_code == 304:
                return search_results["results"][0]
            put_resp.raise_for_status()
            return put_resp.json()
        raise


async def _create_test(client: httpx.AsyncClient, yaml_source: str) -> dict:
    headers = {"Content-Type": "application/x-yaml"}
    try:
        resp = await client.post("/tests", content=yaml_source, headers=headers)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (409, 422):
            doc = yaml.safe_load(yaml_source)
            ns = doc.get("namespace")
            tid = doc.get("id")
            if not ns or not tid:
                raise ValueError(
                    "YAML must include 'namespace' and 'id' fields for update."
                )
            put_resp = await client.put(
                f"/tests/{ns}/{tid}", content=yaml_source, headers=headers
            )
            put_resp.raise_for_status()
            return put_resp.json()
        raise
