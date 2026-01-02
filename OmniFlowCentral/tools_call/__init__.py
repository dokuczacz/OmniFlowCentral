import json
import logging
import os
import time

import azure.functions as func
from azure.storage.blob import ContainerClient
from OmniFlowCentral.shared.request_contract import parse_request


def _get_connection_string():
    return os.environ.get("AZURE_STORAGE_CONNECTION_STRING") or os.environ.get("AzureWebJobsStorage")


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("tools_call: start")

    try:
        contract = parse_request(req)
        tool = contract.get("tool") or ""
        if not tool:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'tool' parameter"}),
                status_code=400,
                mimetype="application/json",
            )

        conn_str = _get_connection_string()
        if not conn_str:
            logging.error("Missing Azure storage connection string")
            return func.HttpResponse(
                json.dumps({"error": "Missing storage connection string"}),
                status_code=500,
                mimetype="application/json",
            )

        container_name = os.environ.get("AZURE_BLOB_CONTAINER_NAME")
        if not container_name:
            logging.error("Missing AZURE_BLOB_CONTAINER_NAME env var")
            return func.HttpResponse(
                json.dumps({"error": "Missing AZURE_BLOB_CONTAINER_NAME"}),
                status_code=500,
                mimetype="application/json",
            )

        # Implement supported tools
        if tool == "list_blobs":
            payload = contract.get("payload", {}) or {}
            prefix = req.params.get("prefix") or payload.get("prefix")
            max_results = 200
            try:
                max_results = int(req.params.get("max_results") or payload.get("max_results") or max_results)
            except Exception:
                max_results = 200
            if max_results < 0:
                max_results = 0
            if max_results > 1000:
                max_results = 1000

            timeout_s = 10
            try:
                timeout_s = int(os.environ.get("AZURE_BLOB_LIST_TIMEOUT_SECONDS") or timeout_s)
            except Exception:
                timeout_s = 10
            if timeout_s < 1:
                timeout_s = 1
            if timeout_s > 60:
                timeout_s = 60

            try:
                client = ContainerClient.from_connection_string(conn_str, container_name)
                blobs = []
                start = time.monotonic()
                for b in client.list_blobs(name_starts_with=prefix, timeout=timeout_s):
                    blobs.append({"name": b.name, "size": getattr(b, "size", None)})
                    if len(blobs) >= max_results:
                        break
                    if (time.monotonic() - start) > timeout_s:
                        break

                return func.HttpResponse(
                    json.dumps({"blobs": blobs}, ensure_ascii=False),
                    status_code=200,
                    mimetype="application/json",
                )
            except Exception as e:
                logging.exception("Error listing blobs (tools_call)")
                return func.HttpResponse(
                    json.dumps({"error": str(e)}),
                    status_code=500,
                    mimetype="application/json",
                )

        if tool == "get_blob":
            payload = contract.get("payload", {}) or {}
            name = req.params.get("name") or payload.get("name")
            if not name:
                return func.HttpResponse(
                    json.dumps({"error": "Missing 'name' parameter for get_blob"}),
                    status_code=400,
                    mimetype="application/json",
                )
            try:
                client = ContainerClient.from_connection_string(conn_str, container_name)
                blob_client = client.get_blob_client(name)
                stream = blob_client.download_blob()
                data = stream.readall()
                try:
                    text = data.decode("utf-8")
                except Exception:
                    text = data.decode("utf-8", errors="replace")

                return func.HttpResponse(
                    json.dumps({"name": name, "content": text}, ensure_ascii=False),
                    status_code=200,
                    mimetype="application/json",
                )
            except Exception as e:
                logging.exception("Error getting blob (tools_call)")
                return func.HttpResponse(
                    json.dumps({"error": str(e)}),
                    status_code=500,
                    mimetype="application/json",
                )

        return func.HttpResponse(
            json.dumps({"error": f"Unsupported tool: {tool}"}),
            status_code=400,
            mimetype="application/json",
        )

    except Exception:
        logging.exception("Unexpected error in tools_call")
        return func.HttpResponse(
            json.dumps({"error": "internal error"}),
            status_code=500,
            mimetype="application/json",
        )
