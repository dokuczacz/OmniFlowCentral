import json
import logging
import os

import azure.functions as func
from azure.storage.blob import ContainerClient


def _get_connection_string():
    return os.environ.get("AZURE_STORAGE_CONNECTION_STRING") or os.environ.get("AzureWebJobsStorage")


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("delete_blob: start")

    try:
        try:
            body = req.get_json()
        except Exception:
            body = {}

        name = req.params.get("name") or body.get("name")
        if not name:
            return func.HttpResponse(json.dumps({"error": "Missing 'name'"}), status_code=400, mimetype="application/json")

        conn_str = _get_connection_string()
        if not conn_str:
            logging.error("Missing Azure storage connection string")
            return func.HttpResponse(json.dumps({"error": "Missing storage connection string"}), status_code=500, mimetype="application/json")

        container_name = os.environ.get("AZURE_BLOB_CONTAINER_NAME")
        if not container_name:
            logging.error("Missing AZURE_BLOB_CONTAINER_NAME env var")
            return func.HttpResponse(json.dumps({"error": "Missing AZURE_BLOB_CONTAINER_NAME"}), status_code=500, mimetype="application/json")

        client = ContainerClient.from_connection_string(conn_str, container_name)
        blob_client = client.get_blob_client(name)
        blob_client.delete_blob()

        return func.HttpResponse(json.dumps({"result": "deleted", "name": name}), status_code=200, mimetype="application/json")
    except Exception:
        logging.exception("Error in delete_blob")
        return func.HttpResponse(json.dumps({"error": "internal"}), status_code=500, mimetype="application/json")
