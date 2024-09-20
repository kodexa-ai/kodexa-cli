#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is the Kodexa CLI, it can be used to allow you to work with an instance of the Kodexa platform.

It supports interacting with the API, listing and viewing components.  Note it can also be used to login and logout
"""
import json
import logging
import os
import os.path
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from shutil import copyfile
from typing import Optional

import click
import pkg_resources
import requests
import yaml
from functional import seq
from kodexa.model import ModelContentMetadata
from kodexa.platform.client import (
    ModelStoreEndpoint,
    PageDocumentFamilyEndpoint,
    DocumentFamilyEndpoint,
)
from kodexa_cli.documentation import get_path
from rich import print
from rich.prompt import Confirm

logging.root.addHandler(logging.StreamHandler(sys.stdout))

from kodexa import KodexaClient, Taxonomy
from kodexa.platform.kodexa import KodexaPlatform

global GLOBAL_IGNORE_COMPLETE

LOGGING_LEVELS = {
    0: logging.NOTSET,
    1: logging.ERROR,
    2: logging.WARN,
    3: logging.INFO,
    4: logging.DEBUG,
}  #: a mapping of `verbose` option counts to logging levels

DEFAULT_COLUMNS = {
    "extensionPacks": ["ref", "name", "description", "type", "status"],
    "projects": ["id", "organization.name", "name", "description"],
    "assistants": ["ref", "name", "description", "template"],
    "executions": [
        "id",
        "start_date",
        "end_date",
        "status",
        "assistant_name",
        "filename",
    ],
    "memberships": ["organization.slug", "organization.name"],
    "stores": ["ref", "name", "description", "store_type", "store_purpose", "template"],
    "organizations": [
        "id",
        "slug",
        "name",
    ],
    "default": ["ref", "name", "description", "type", "template"],
}


def get_current_kodexa_profile():
    try:
        return KodexaPlatform.get_current_profile()
    except:
        return ""


def get_current_kodexa_url():
    try:
        return KodexaPlatform.get_url()
    except:
        return ""


def get_current_access_token():
    try:
        return KodexaPlatform.get_access_token()
    except:
        return ""


@contextmanager
def set_directory(path: Path):
    """Sets the cwd within the context

    Args:
        path (Path): The path to the cwd

    Yields:
        None
    """

    origin = Path().absolute()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(origin)


class Info(object):
    """An information object to pass data between CLI functions."""

    def __init__(self):  # Note: This object must have an empty constructor.
        """Create a new instance."""
        self.verbose: int = 0


# pass_info is a decorator for functions that pass 'Info' objects.
#: pylint: disable=invalid-name
pass_info = click.make_pass_decorator(Info, ensure=True)


def merge(a, b, path=None):
    """
    merges dictionary b into dictionary a

    :param a: dictionary a
    :param b: dictionary b
    :param path: path to the current node
    :return: merged dictionary
    """
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                raise Exception("Conflict at %s" % ".".join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


class MetadataHelper:
    """ """

    @staticmethod
    def load_metadata(path, filename: Optional[str]) -> dict:
        if filename is not None:
            dharma_metadata_file = open(os.path.join(path, filename))
            if filename.endswith(".json"):
                dharma_metadata = json.loads(dharma_metadata_file.read())
            elif filename.endswith(".yml"):
                dharma_metadata = yaml.safe_load(dharma_metadata_file.read())
        elif os.path.exists(os.path.join(path, "dharma.json")):
            dharma_metadata_file = open(os.path.join(path, "dharma.json"))
            dharma_metadata = json.loads(dharma_metadata_file.read())
        elif os.path.exists(os.path.join(path, "dharma.yml")):
            dharma_metadata_file = open(os.path.join(path, "dharma.yml"))
            dharma_metadata = yaml.safe_load(dharma_metadata_file.read())
        elif os.path.exists(os.path.join(path, "kodexa.yml")):
            dharma_metadata_file = open(os.path.join(path, "kodexa.yml"))
            dharma_metadata = yaml.safe_load(dharma_metadata_file.read())
        else:
            raise Exception(
                "Unable to find a kodexa.yml file describing your extension"
            )
        return dharma_metadata


# Change the options to below to suit the actual options for your task (or
# tasks).
@click.group()
@click.option("--verbose", "-v", count=True, help="Enable verbose output.")
@pass_info
def cli(info: Info, verbose: int):
    # Use the verbosity count to determine the logging level...
    if verbose > 0:
        logging.root.setLevel(
            LOGGING_LEVELS[verbose] if verbose in LOGGING_LEVELS else logging.DEBUG
        )
        click.echo(
            click.style(
                f"Verbose logging is enabled. "
                f"(LEVEL={logging.root.getEffectiveLevel()})",
                fg="yellow",
            )
        )
    info.verbose = verbose


def safe_entry_point():
    """
    This function is a safe entry point that handles any exceptions
    that occur when the cli() function is called. It prints the time
    the function started and ended, as well as any exceptions that occur.

    This function is primarily used as a wrapper to ensure that any exceptions
    that occur during execution are handled gracefully and that the execution
    time is logged for debugging or performance tuning purposes.
    """
    # Assuming that execution is successful initially
    success = True
    global GLOBAL_IGNORE_COMPLETE
    GLOBAL_IGNORE_COMPLETE = False
    print("")
    try:
        # Record the starting time of the function execution
        start_time = datetime.now().replace(microsecond=0)

        cli_version = pkg_resources.get_distribution("kodexa").version

        # Check Pypi for the latest version
        try:
            latest_version = seq(["https://pypi.org/pypi/kodexa/json"]).map(
                lambda url: json.loads(requests.get(url).text)
            ).map(lambda data: data["info"]["version"]).first()

            if latest_version != cli_version:
                print(
                    f"New version of Kodexa CLI available: {latest_version} (you have {cli_version})"
                )
        except:
            print("Unable to check for latest version")

        try:
            print(f"Using profile {get_current_kodexa_profile()} @ {get_current_kodexa_url()}\n")
        except:
            print("Unable to load profile")

        # Call the cli() function
        cli()
    except Exception as e:
        # If an exception occurs, mark success as False and print the exception
        success = False
        print(f"\n:fire: [red][bold]Failed[/bold]: {e}[/red]")
    finally:
        # If the execution was successful
        if success and not GLOBAL_IGNORE_COMPLETE:
            # Record the end time of the function execution
            end_time = datetime.now().replace(microsecond=0)

            # Print the end time and the time taken for function execution
            print(
                f"\n:timer_clock: Completed @ {end_time} (took {end_time - start_time}s)"
            )


@cli.command()
@click.argument("ref", required=True)
@click.argument("paths", required=True, nargs=-1)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--threads", default=5, help="Number of threads to use")
@click.option("--token", default=get_current_access_token(), help="Access token")
@click.option("--external-data/--no-external-data", default=False,
              help="Look for a .json file that has the same name as the upload and attach this as external data")
@pass_info
def upload(_: Info, ref: str, paths: list[str], token: str, url: str, threads: int, external_data: bool = False):
    """
    Upload a file to the Kodexa platform.

    ref is the reference to the document store to upload to.
    path is the path to the file to upload, it can be many files.
    threads is the number of threads to use for the upload (default is 5)
    """

    client = KodexaClient(url=url, access_token=token)
    document_store = client.get_object_by_ref("store", ref)

    from kodexa.platform.client import DocumentStoreEndpoint

    print(f"Uploading {len(paths)} files to {ref}\n")
    if isinstance(document_store, DocumentStoreEndpoint):
        from rich.progress import track

        def upload_file(path, external_data):
            try:
                if external_data:
                    external_data_path = f"{os.path.splitext(path)[0]}.json"
                    if os.path.exists(external_data_path):
                        with open(external_data_path, "r") as f:
                            external_data = json.load(f)
                            document_store.upload_file(path, external_data=external_data)
                            return f"Successfully uploaded {path} with external data {json.dumps(external_data)}"
                    else:
                        return f"External data file not found for {path}"
                else:
                    document_store.upload_file(path)
                    return f"Successfully uploaded {path}"
            except Exception as e:
                return f"Error uploading {path}: {e}"

        from concurrent.futures import ThreadPoolExecutor

        # Using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=threads) as executor:
            upload_args = [(path, external_data) for path in paths]
            for result in track(
                    executor.map(lambda args: upload_file(*args), upload_args),
                    total=len(paths),
                    description="Uploading files",
            ):
                print(result)
        print("Upload complete :tada:")
    else:
        print(f"{ref} is not a document store")


@cli.command
@click.option(
    "--org", help="The slug for the organization to deploy to", required=False
)
@click.option(
    "--slug",
    help="Override the slug for component (only works for a single component)",
    required=False,
)
@click.option(
    "--version",
    help="Override the version for component (only works for a single component)",
    required=False,
)
@click.option("--file", help="The path to the file containing the object to apply")
@click.option(
    "--update/--no-update",
    help="The path to the file containing the object to apply",
    default=False,
)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@click.option(
    "--format", default=None, help="The format to input if from stdin (json, yaml)"
)
@click.option(
    "--overlay", default=None, help="A JSON or YAML file that will overlay the metadata"
)
@click.argument("files", nargs=-1)
@pass_info
def deploy(
        _: Info,
        org: Optional[str],
        file: str,
        files: list[str],
        url: str,
        token: str,
        format=None,
        update: bool = False,
        version=None,
        overlay: Optional[str] = None,
        slug=None,
):
    """
    Deploy a component to a Kodexa platform instance from a file or stdin
    """

    client = KodexaClient(access_token=token, url=url)

    def deploy_obj(obj):
        if "deployed" in obj:
            del obj["deployed"]

        overlay_obj = None

        if overlay is not None:
            print("Reading overlay")
            if overlay.endswith("yaml") or overlay.endswith("yml"):
                overlay_obj = yaml.safe_load(sys.stdin.read())
            elif overlay.endswith("json"):
                overlay_obj = json.loads(sys.stdin.read())
            else:
                raise Exception(
                    "Unable to determine the format of the overlay file, must be .json or .yml/.yaml"
                )

        if isinstance(obj, list):
            print(f"Found {len(obj)} components")
            for o in obj:
                if overlay_obj:
                    o = merge(o, overlay_obj)

                component = client.deserialize(o)
                if org is not None:
                    component.org_slug = org
                print(
                    f"Deploying component {component.slug}:{component.version} to {client.get_url()}"
                )
                from datetime import datetime

                start = datetime.now()
                component.deploy(update=update)
                from datetime import datetime

                print(
                    f"Deployed at {datetime.now()}, took {datetime.now() - start} seconds"
                )

        else:
            if overlay_obj:
                obj = merge(obj, overlay_obj)

            component = client.deserialize(obj)

            if version is not None:
                component.version = version
            if slug is not None:
                component.slug = slug
            if org is not None:
                component.org_slug = org
            print(f"Deploying component {component.slug}:{component.version}")
            log_details = component.deploy(update=update)
            for log_detail in log_details:
                print(log_detail)

    if files is not None:
        from rich.progress import track

        for idx in track(
                range(len(files)), description=f"Deploying {len(files)} files"
        ):
            obj = {}
            file = files[idx]
            with open(file, "r") as f:
                if file.lower().endswith(".json"):
                    obj.update(json.load(f))
                elif file.lower().endswith(".yaml") or file.lower().endswith(".yml"):
                    obj.update(yaml.safe_load(f))
                else:
                    raise Exception("Unsupported file type")

                deploy_obj(obj)
    elif file is None:
        print("Reading from stdin")
        if format == "yaml" or format == "yml":
            obj = yaml.safe_load(sys.stdin.read())
        elif format == "json":
            obj = json.loads(sys.stdin.read())
        else:
            raise Exception("You must provide a format if using stdin")

        deploy_obj(obj)
    else:
        print("Reading from file", file)
        with open(file, "r") as f:
            if file.lower().endswith(".json"):
                obj = json.load(f)
            elif file.lower().endswith(".yaml") or file.lower().endswith(".yml"):
                obj = yaml.safe_load(f)
            else:
                raise Exception("Unsupported file type")

            deploy_obj(obj)

    print("Deployed :tada:")


@cli.command()
@click.argument("execution_id", required=True)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def logs(_: Info, execution_id: str, url: str, token: str):
    """
    Get the logs for a specific execution

    execution_id is the id of the execution to get the logs for
    """
    client = KodexaClient(url=url, access_token=token)
    response = client.executions.get(execution_id).logs()

    if response.status_code == 200:  # Check if the response is successful
        logs_data = response.json()  # Parse the JSON data from the response
        # Print the logs using rich's print function
        print(logs_data)
    else:
        print(f"Failed to retrieve logs. Status code: {response.status_code}")


@cli.command()
@click.argument("ref", required=True)
@click.argument("output_file", required=False, default="model_implementation")
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def download_implementation(_: Info, ref: str, output_file: str, url: str, token: str):
    """
    Download the implementation of a model store
    """
    # We are going to download the implementation of the component
    client = KodexaClient(url=url, access_token=token)
    model_store_endpoint: ModelStoreEndpoint = client.get_object_by_ref("store", ref)
    model_store_endpoint.download_implementation(output_file)


@cli.command()
@click.argument("object_type", required=True)
@click.argument("ref", required=False)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@click.option("--query", default="*", help="Limit the results using a query")
@click.option("--format", default=None, help="The format to output (json, yaml)")
@click.option("--page", default=1, help="Page number")
@click.option("--pageSize", default=10, help="Page size")
@click.option("--sort", default=None, help="Sort by (ie. startDate:desc)")
@click.option("--truncate/--no-truncate", default=True, help="Truncate the output or not")
@pass_info
def get(
        _: Info,
        object_type: str,
        ref: Optional[str],
        url: str,
        token: str,
        query: str,
        format=None,
        page: int = 1,
        pagesize: int = 10,
        sort: str = None,
        truncate: bool = True,
):
    """
    List the instances of the component or entity type

    object_type is the type of object to list (component, document, execution, etc.)
    ref is the reference to the object
    """

    client = KodexaClient(url=url, access_token=token)

    from kodexa.platform.client import resolve_object_type

    object_name, object_metadata = resolve_object_type(object_type)
    global GLOBAL_IGNORE_COMPLETE

    if "global" in object_metadata and object_metadata["global"]:
        objects_endpoint = client.get_object_type(object_type)
        if ref and not ref.isspace():
            object_instance = objects_endpoint.get(ref)

            if format == "json":
                print(
                    json.dumps(object_instance.model_dump(by_alias=True), indent=4),
                    "json",
                )
                GLOBAL_IGNORE_COMPLETE = True
            elif format == "yaml":
                object_dict = object_instance.model_dump(by_alias=True)
                print(yaml.dump(object_dict, indent=4), "yaml")
                GLOBAL_IGNORE_COMPLETE = True
        else:
            print_object_table(
                object_metadata, objects_endpoint, query, page, pagesize, sort, truncate
            )
    else:
        if ref and not ref.isspace():
            if "/" in ref:
                object_instance = client.get_object_by_ref(
                    object_metadata["plural"], ref
                )

                if format == "json":
                    print(
                        json.dumps(
                            object_instance.model_dump(by_alias=True), indent=4
                        )
                    )
                    GLOBAL_IGNORE_COMPLETE = True
                elif format == "yaml" or not format:
                    object_dict = object_instance.model_dump(by_alias=True)
                    print(yaml.dump(object_dict, indent=4))
                    GLOBAL_IGNORE_COMPLETE = True
            else:
                organization = client.organizations.find_by_slug(ref)

                if organization is None:
                    print(f"Could not find organization with slug {ref}")
                    exit(1)

                objects_endpoint = client.get_object_type(object_type, organization)
                print_object_table(
                    object_metadata, objects_endpoint, query, page, pagesize, sort, truncate
                )
        else:
            print(f"You must provide a ref to get a specific object")
            exit(1)


def print_object_table(object_metadata, objects_endpoint, query, page, pagesize, sort, truncate):
    """
    Print the output of the list in a table form

    """
    from rich.table import Table

    table = Table(title=f"Listing {object_metadata['plural']}", title_style="bold blue")
    # Get column list for the referenced object

    if object_metadata["plural"] in DEFAULT_COLUMNS:
        column_list = DEFAULT_COLUMNS[object_metadata["plural"]]
    else:
        column_list = DEFAULT_COLUMNS["default"]

    # Create column header for the table
    for col in column_list:
        if truncate:
            table.add_column(col)
        else:
            table.add_column(col, overflow="fold")

    try:
        page_of_object_endpoints = objects_endpoint.list(
            query=query, page=page, page_size=pagesize, sort=sort
        )
    except Exception as e:
        print("e:", e)
        raise e
    # Get column values
    for objects_endpoint in page_of_object_endpoints.content:
        row = []
        for col in column_list:
            if col == "filename":
                filename = ""
                for content_object in objects_endpoint.content_objects:
                    if content_object.metadata and "path" in content_object.metadata:
                        filename = content_object.metadata["path"]
                        break  # Stop searching if path is found
                row.append(filename)
            elif col == "assistant_name":
                assistant_name = ""
                if objects_endpoint.pipeline and objects_endpoint.pipeline.steps:
                    for step in objects_endpoint.pipeline.steps:
                        assistant_name = step.name
                        break  # Stop searching if path is found
                row.append(assistant_name)
            else:
                try:
                    value = str(getattr(objects_endpoint, col))
                    row.append(value)
                except AttributeError:
                    row.append("")
        table.add_row(*row, style="yellow")

    from rich.console import Console

    console = Console()
    console.print(table)
    console.print(
        f"Page [bold]{page_of_object_endpoints.number + 1}[/bold] of [bold]{page_of_object_endpoints.total_pages}[/bold] "
        f"(total of {page_of_object_endpoints.total_elements} objects)"
    )


@cli.command()
@click.argument("ref", required=True)
@click.argument("query", nargs=-1)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@click.option(
    "--download/--no-download",
    default=False,
    help="Download the KDDB for the latest in the family",
)
@click.option(
    "--download-native/--no-download-native",
    default=False,
    help="Download the native file for the family",
)
@click.option(
    "--stream/--no-stream",
    default=False,
    help="Stream the document families, don't paginate",
)
@click.option("--page", default=1, help="Page number")
@click.option("--pageSize", default=10, help="Page size", type=int)
@click.option(
    "--limit", default=None, help="Limit the number of results in streaming", type=int
)
@click.option(
    "--filter/--no-filter", default=False, help="Switch from query to filter syntax"
)
@click.option(
    "--delete/--no-delete", default=False, help="Delete the matching document families"
)
@click.option(
    "--reprocess", default=None, help="Reprocess using the provided assistant ID"
)
@click.option(
    "--watch",
    default=None,
    help="Watch the results, refresh every n seconds",
    type=int,
)
@click.option(
    "--threads",
    default=5,
    help="Number of threads to use (only in streaming)",
    type=int,
)
@click.option("--sort", default=None, help="Sort by ie. name:asc")
@pass_info
def query(
        _: Info,
        query: list[str],
        ref: str,
        url: str,
        token: str,
        download: bool,
        download_native: bool,
        page: int,
        pagesize: int,
        sort: None,
        filter: None,
        reprocess: Optional[str] = None,
        delete: bool = False,
        stream: bool = False,
        threads: int = 5,
        limit: Optional[int] = None,
        watch: Optional[int] = None,
):
    """
    Query the documents in a given document store

    ref is the reference to the document store
    query is the query to run
    reprocess is the assistant id to use for reprocessing
    delete will delete the document families that match the query

    """
    client = KodexaClient(url=url, access_token=token)
    from kodexa.platform.client import DocumentStoreEndpoint

    query = " ".join(list(query))

    document_store: DocumentStoreEndpoint = client.get_object_by_ref("store", ref)

    while True:
        if isinstance(document_store, DocumentStoreEndpoint):
            if stream:
                if filter:
                    print(f"Streaming filter: {query}\n")
                    page_of_document_families = document_store.stream_filter(
                        query, sort, limit
                    )
                else:
                    print(f"Streaming query: {query}\n")
                    page_of_document_families = document_store.stream_query(
                        query, sort, limit
                    )
            else:
                if filter:
                    print(f"Using filter: {query}\n")
                    page_of_document_families: PageDocumentFamilyEndpoint = (
                        document_store.filter(query, page, pagesize, sort)
                    )
                else:
                    print(f"Using query: {query}\n")
                    page_of_document_families: PageDocumentFamilyEndpoint = (
                        document_store.query(query, page, pagesize, sort)
                    )

            if not stream:
                from rich.table import Table

                table = Table(title=f"Listing Document Family", title_style="bold blue")
                column_list = ["path", "created", "modified", "size"]
                # Create column header for the table
                for col in column_list:
                    table.add_column(col)

                # Get column values
                for objects_endpoint in page_of_document_families.content:
                    row = []
                    for col in column_list:
                        try:
                            value = str(getattr(objects_endpoint, col))
                            row.append(value)
                        except AttributeError:
                            row.append("")
                    table.add_row(*row, style="yellow")

                from rich.console import Console

                console = Console()
                console.print(table)
                total_pages = (
                    page_of_document_families.total_pages
                    if page_of_document_families.total_pages > 0
                    else 1
                )
                console.print(
                    f"\nPage [bold]{page_of_document_families.number + 1}[/bold] of [bold]{total_pages}[/bold] "
                    f"(total of {page_of_document_families.total_elements} document families)"
                )

            # We want to go through all the endpoints to do the other actions
            document_families = (
                page_of_document_families
                if stream
                else page_of_document_families.content
            )

            if delete and not Confirm.ask(
                    "You are sure you want to delete these families (this action can not be reverted)?"
            ):
                print("Aborting delete")
                exit(1)

            import concurrent.futures

            if reprocess is not None:
                # We need to get the assistant so we can reprocess
                assistant = client.assistants.get(reprocess)
                if assistant is None:
                    print(f"Unable to find assistant with id {reprocess}")
                    exit(1)

                if not stream:
                    print("You can't reprocess without streaming")
                    exit(1)

                print(f"Reprocessing with assistant {assistant.name}")

            if stream:
                print(f"Streaming document families (with {threads} threads)")
                with concurrent.futures.ThreadPoolExecutor(
                        max_workers=threads
                ) as executor:

                    def process_family(document_family):
                        if download:
                            print(f"Downloading document for {document_family.path}")
                            document_family: DocumentFamilyEndpoint = document_family
                            document_family.get_document().to_kddb().save(
                                document_family.path + ".kddb"
                            )
                        if download_native:
                            print(
                                f"Downloading native object for {document_family.path}"
                            )
                            with open(document_family.path + ".native", "wb") as f:
                                f.write(document_family.get_native())

                        if delete:
                            print(f"Deleting {document_family.path}")
                            document_family.delete()

                        if reprocess is not None:
                            print(f"Reprocessing {document_family.path}")
                            document_family.reprocess(assistant)

                    executor.map(process_family, document_families)

        else:
            raise Exception("Unable to find document store with ref " + ref)

        if not watch:
            break
        else:
            import time

            time.sleep(watch)


@cli.command()
@click.argument("project_id", required=True)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@click.option("--output", help="The path to export to")
@pass_info
def export_project(_: Info, project_id: str, url: str, token: str, output: str):
    """
    Export a project, and associated resources to a local zip file

    project_id is the id of the project to export
    """
    client = KodexaClient(url, token)
    project_endpoint = client.projects.get(project_id)
    client.export_project(project_endpoint, output)


@cli.command()
@click.argument("org_slug", required=True)
@click.argument("path", required=True)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def import_project(_: Info, org_slug: str, url: str, token: str, path: str):
    """
    Import a project, and associated resources from a local zip file

    org_slug is the slug of the organization to import into
    path is the path to the zip file

    """
    print("Importing project from {}".format(path))

    client = KodexaClient(url, token)
    organization = client.organizations.find_by_slug(org_slug)

    print("Organization: {}".format(organization.name))
    client.import_project(organization, path)

    print("Project imported")


@cli.command()
@click.argument("project_id", required=True)
@click.argument("assistant_id", required=True)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@click.option("--file", help="The path to the file containing the event to send")
@click.option(
    "--format", default=None, help="The format to use if from stdin (json, yaml)"
)
@pass_info
def send_event(
        _: Info,
        project_id: str,
        assistant_id: str,
        url: str,
        file: str,
        event_format: str,
        token: str,
):
    """
    Send an event to an assistant

    project_id is the id of the project to send the event to
    assistant_id is the id of the assistant to send the event to

    """

    client = KodexaClient(url, token)

    obj = None
    if file is None:
        print("Reading from stdin")
        if event_format == "yaml":
            obj = yaml.parse(sys.stdin.read())
        elif event_format == "json":
            obj = json.loads(sys.stdin.read())
        else:
            raise Exception("You must provide a format if using stdin")
    else:
        print("Reading event from file", file)
        with open(file, "r") as f:
            if file.lower().endswith(".json"):
                obj = json.load(f)
            elif file.lower().endswith(".yaml"):
                obj = yaml.full_load(f)
            else:
                raise Exception("Unsupported file type")

    print("Sending event")
    from kodexa.platform.client import AssistantEndpoint

    assistant_endpoint: AssistantEndpoint = client.get_project(
        project_id
    ).assistants.get(assistant_id)
    assistant_endpoint.send_event(obj["eventType"], obj["options"])
    print("Event sent :tada:")


@cli.command()
@pass_info
@click.option(
    "--python/--no-python", default=False, help="Print out the header for a Python file"
)
@click.option(
    "--show-token/--no-show-token", default=False, help="Show access token"
)
def platform(_: Info, python: bool, show_token: bool):
    """
    Get the details for the Kodexa instance we are logged into
    """

    print(f"Profile: {get_current_kodexa_profile()}")
    platform_url = get_current_kodexa_url()

    if platform_url is not None:
        print(f"URL: {get_current_kodexa_url()}")

        if show_token:
            print(f"Access Token: {get_current_access_token()}")

        kodexa_version = KodexaPlatform.get_server_info()

        print(f"Environment: {kodexa_version['environment']}")
        print(f"Version: {kodexa_version['version']}")
        print(f"Release: {kodexa_version['release']}")

        if python:
            print("\nPython example:\n\n")
            print(f"from kodexa import KodexaClient")
            print(
                f"client = KodexaClient('{get_current_kodexa_url()}', '{get_current_access_token()}')"
            )
    else:
        print("Kodexa is not logged in")


@cli.command()
@click.argument("object_type")
@click.argument("ref")
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@click.option("-y", "--yes", is_flag=True, help="Don't ask for confirmation")
@pass_info
def delete(_: Info, object_type: str, ref: str, url: str, token: str, yes: bool):
    """
    Delete the given resource (based on ref)

    object_type is the type of object to delete (e.g. 'project', 'assistant', 'store')
    ref is the ref of the object to delete
    """
    client = KodexaClient(url, token)
    client = KodexaClient(url=url, access_token=token)

    from kodexa.platform.client import resolve_object_type

    object_name, object_metadata = resolve_object_type(object_type)

    if "global" in object_metadata and object_metadata["global"]:
        objects_endpoint = client.get_object_type(object_type)
        object_endpoint = objects_endpoint.get(ref)

        if not yes:
            confirm_delete = Confirm.ask(
                f"Please confirm you want to delete {object_metadata['name']} {object_endpoint.name}?"
            )
            if confirm_delete:
                print(f"Deleting {object_type} {ref}")
                object_endpoint.delete()
                print(f"Deleted")
            else:
                print(f"Deleting {object_type} {ref}")
                object_endpoint.delete()
                print(f"Deleted")
    else:
        if ref and not ref.isspace():
            object_endpoint = client.get_object_by_ref(object_metadata["plural"], ref)
            if not yes:
                confirm_delete = Confirm.ask(
                    f"Please confirm you want to delete {object_metadata['name']} {object_endpoint.ref}?"
                )
                if confirm_delete:
                    print(f"Deleting {object_type} {ref}")
                    object_endpoint.delete()
                    print(f"Deleted")
            else:
                print(f"Deleting {object_type} {ref}")
                object_endpoint.delete()
                print(f"Deleted")
        else:
            print(f"You must provide a ref to get a specific object")
            exit(1)


@cli.command()
@pass_info
@click.argument("profile", required=False)
@click.option(
    "--delete/--no-delete", default=False, help="Delete the named profile"
)
@click.option(
    "--list/--no-list", default=False, help="List profile names"
)
def profile(_: Info, profile: str, delete: bool, list: bool):
    """
    With no args it will print the current profile, if you provide an argument it will set the profile
    with the --delete option it will delete the provided profile
    """
    if profile:
        if delete:
            print(f"Deleting profile {profile}")
            KodexaPlatform.delete_profile(profile)
        else:
            print(f"Setting profile to {profile}")
            KodexaPlatform.set_profile(profile)
    else:
        if list:
            print(f"Profiles: {','.join(KodexaPlatform.list_profiles())}")
        else:
            print(
                f"Current profile: {get_current_kodexa_profile()} [{KodexaPlatform.get_url(get_current_kodexa_profile())}]")



@cli.command()
@pass_info
@click.argument("taxonomy_file", required=False)
@click.option("--output-path", default=".", help="The path to output the dataclasses")
@click.option("--output-file", default="dataclasses.py", help="The file to output the dataclasses to")
def dataclasses(_: Info, taxonomy_file: str, output_path: str, output_file: str):
    """
    Generate dataclasses based on a taxonomy file
    """
    if taxonomy_file is None:
        print("You must provide a taxonomy file")
        exit(1)

    with open(taxonomy_file, "r") as f:

        if taxonomy_file.endswith(".json"):
            taxonomy = json.load(f)
        else:
            taxonomy = yaml.safe_load(f)

    taxonomy = Taxonomy(**taxonomy)

    from kodexa.dataclasses import build_llm_data_classes_for_taxonomy
    build_llm_data_classes_for_taxonomy(taxonomy, output_path, output_file)


@cli.command()
@pass_info
def login(_: Info):
    """Logs into the specified platform environment using the email address and password provided,
    then downloads and stores the personal access token (PAT) of the user.

    Once successfully logged in, calls to remote actions, pipelines, and workflows will be made to the
    platform that was set via this login function and will use the stored PAT for authentication.

    """
    try:
        kodexa_url = input("Enter the Kodexa URL (https://platform.kodexa.ai): ")

        # Lets stop the common issues
        kodexa_url = kodexa_url.strip()

        # Remove the trailing slash
        if kodexa_url.endswith("/"):
            kodexa_url = kodexa_url[:-1]

        if kodexa_url == "":
            print("Using default as https://platform.kodexa.ai")
            kodexa_url = "https://platform.kodexa.ai"
        token = input("Enter your token: ")
        profile_name = input("Enter your profile name (default): ")
    except Exception as error:
        import better_exceptions
        import sys
        print("\n".join(
            better_exceptions.format_exception(*sys.exc_info())))
    else:
        try:
            KodexaPlatform.login(kodexa_url, token, profile_name)
        except Exception as error:
            import better_exceptions
            import sys
            print("\n".join(
                better_exceptions.format_exception(*sys.exc_info())))


@cli.command()
@click.argument("files", nargs=-1)
@pass_info
def mkdocs(_: Info, files: list[str]):
    """
    Generate mkdocs documentation for components

    file_pattern is the pattern to use to find the kodexa.yml files (default is **/kodexa.yml)

    """

    class Loader(yaml.SafeLoader):
        pass

    def construct_undefined(self, node):
        if isinstance(node, yaml.nodes.ScalarNode):
            value = self.construct_scalar(node)
        elif isinstance(node, yaml.nodes.SequenceNode):
            value = self.construct_sequence(node)
        elif isinstance(node, yaml.nodes.MappingNode):
            value = self.construct_mapping(node)
        else:
            assert False, f"unexpected node: {node!r}"

    Loader.add_constructor(None, construct_undefined)

    metadata_components = []
    for path in files:
        print("Loading metadata from ", path)
        if path.endswith(".json"):
            print("Loading from json")
            components = json.loads(open(path).read())
        else:
            print("Loading from yaml")
            components = yaml.load(open(path).read(), Loader=Loader)

        if not isinstance(components, list):
            components = [components]

        print(f"Loaded {len(components)} from ", path)
        metadata_components.extend(components)

    from kodexa_cli.documentation import generate_documentation

    generate_documentation(metadata_components)


@cli.command()
@pass_info
def version(_: Info):
    """
    Get the version of the CLI

    """
    print("Kodexa Version:", pkg_resources.get_distribution("kodexa").version)


@cli.command()
@click.option(
    "--path",
    default=os.getcwd(),
    help="Path to folder container kodexa.yml (defaults to current)",
)
@click.option(
    "--output",
    default=os.getcwd() + "/dist",
    help="Path to the output folder (defaults to dist under current)",
)
@click.option(
    "--package-name", help="Name of the package (applicable when deploying models"
)
@click.option(
    "--repository", default="kodexa", help="Repository to use (defaults to kodexa)"
)
@click.option(
    "--version", default=os.getenv("VERSION"), help="Version number (defaults to 1.0.0)"
)
@click.option(
    "--strip-version-build/--include-version-build",
    default=False,
    help="Determine whether to include the build from the version number when packaging the resources",
)
@click.option(
    "--update-resource-versions/--no-update-resource-versions",
    default=True,
    help="Determine whether to update the resources to match the resource pack version",
)
@click.option("--helm/--no-helm", default=False, help="Generate a helm chart")
@click.argument("files", nargs=-1)
@pass_info
def package(
        _: Info,
        path: str,
        output: str,
        version: str,
        files: list[str] = None,
        helm: bool = False,
        package_name: Optional[str] = None,
        repository: str = "kodexa",
        strip_version_build: bool = False,
        update_resource_versions: bool = True,
):
    """
    Package an extension pack based on the kodexa.yml file
    """

    if files is None or len(files) == 0:
        files = ["kodexa.yml"]

    packaged_resources = []

    for file in files:
        metadata_obj = MetadataHelper.load_metadata(path, file)

        if "type" not in metadata_obj:
            print("Unable to package, no type in metadata for ", file)
            continue

        print("Processing ", file)

        try:
            os.makedirs(output)
        except OSError as e:
            import errno

            if e.errno != errno.EEXIST:
                raise

        if update_resource_versions:
            if strip_version_build:
                if "-" in version:
                    new_version = version.split("-")[0]
                else:
                    new_version = version

                metadata_obj["version"] = (
                    new_version if new_version is not None else "1.0.0"
                )
            else:
                metadata_obj["version"] = version if version is not None else "1.0.0"

        unversioned_metadata = os.path.join(output, "kodexa.json")

        def build_json():
            versioned_metadata = os.path.join(
                output,
                f"{metadata_obj['type']}-{metadata_obj['slug']}-{metadata_obj['version']}.json",
            )
            with open(versioned_metadata, "w") as outfile:
                json.dump(metadata_obj, outfile)

            # TODO this is a legacy thing, we should remove it in the 6.3.0 release
            versioned_metadata = os.path.join(
                output, f"{metadata_obj['slug']}-{metadata_obj['version']}.json"
            )
            with open(versioned_metadata, "w") as outfile:
                json.dump(metadata_obj, outfile)

            copyfile(versioned_metadata, unversioned_metadata)
            return Path(versioned_metadata).name

        if "type" not in metadata_obj:
            metadata_obj["type"] = "extensionPack"

        if metadata_obj["type"] == "extensionPack":
            if "source" in metadata_obj and "location" in metadata_obj["source"]:
                metadata_obj["source"]["location"] = metadata_obj["source"][
                    "location"
                ].format(**metadata_obj)
            build_json()

            if helm:
                # We will generate a helm chart using a template chart using the JSON we just created
                import subprocess

                unversioned_metadata = os.path.join(output, "kodexa.json")
                copyfile(
                    unversioned_metadata,
                    f"{os.path.dirname(get_path())}/charts/extension-pack/resources/extension.json",
                )

                # We need to update the extension pack chart with the version
                with open(
                        f"{os.path.dirname(get_path())}/charts/extension-pack/Chart.yaml",
                        "r",
                ) as stream:
                    chart_yaml = yaml.safe_load(stream)
                    chart_yaml["version"] = metadata_obj["version"]
                    chart_yaml["appVersion"] = metadata_obj["version"]
                    chart_yaml["name"] = "extension-meta-" + metadata_obj["slug"]
                    with open(
                            f"{os.path.dirname(get_path())}/charts/extension-pack/Chart.yaml",
                            "w",
                    ) as stream:
                        yaml.safe_dump(chart_yaml, stream)

                subprocess.check_call(
                    [
                        "helm",
                        "package",
                        f"{os.path.dirname(get_path())}/charts/extension-pack",
                        "--version",
                        metadata_obj["version"],
                        "--app-version",
                        metadata_obj["version"],
                        "--destination",
                        output,
                    ]
                )

            print("Extension pack has been packaged :tada:")

        elif (
                metadata_obj["type"].upper() == "STORE"
                and metadata_obj["storeType"].upper() == "MODEL"
        ):
            model_content_metadata = ModelContentMetadata.model_validate(
                metadata_obj["metadata"]
            )

            import uuid

            model_content_metadata.state_hash = str(uuid.uuid4())
            metadata_obj["metadata"] = model_content_metadata.model_dump(by_alias=True)
            name = build_json()

            # We need to work out the parent directory
            parent_directory = os.path.dirname(file)
            print("Going to build the implementation zip in", parent_directory)
            with set_directory(Path(parent_directory)):
                # This will create the implementation.zip - we will then need to change the filename
                ModelStoreEndpoint.build_implementation_zip(model_content_metadata)
                versioned_implementation = os.path.join(
                    output,
                    f"{metadata_obj['type']}-{metadata_obj['slug']}-{metadata_obj['version']}.zip",
                )
                copyfile("implementation.zip", versioned_implementation)

                # Delete the implementation
                os.remove("implementation.zip")

            print(
                f"Model has been prepared {metadata_obj['type']}-{metadata_obj['slug']}-{metadata_obj['version']}"
            )
            packaged_resources.append(name)
        else:
            print(
                f"{metadata_obj['type']}-{metadata_obj['slug']}-{metadata_obj['version']} has been prepared"
            )
            name = build_json()
            packaged_resources.append(name)

    if len(packaged_resources) > 0:
        if helm:
            print(
                f"{len(packaged_resources)} resources(s) have been prepared, we now need to package them into a resource package.\n"
            )

            if package_name is None:
                raise Exception(
                    "You must provide a package name when packaging resources"
                )
            if version is None:
                raise Exception("You must provide a version when packaging resources")

            # We need to create an index.json which is a json list of the resource names, versions and types
            with open(os.path.join(output, "index.json"), "w") as index_json:
                json.dump(packaged_resources, index_json)

            # We need to update the extension pack chart with the version
            with open(
                    f"{os.path.dirname(get_path())}/charts/resource-pack/Chart.yaml", "r"
            ) as stream:
                chart_yaml = yaml.safe_load(stream)
                chart_yaml["version"] = version
                chart_yaml["appVersion"] = version
                chart_yaml["name"] = package_name
                with open(
                        f"{os.path.dirname(get_path())}/charts/resource-pack/Chart.yaml",
                        "w",
                ) as stream:
                    yaml.safe_dump(chart_yaml, stream)

            # We need to update the extension pack chart with the version
            with open(
                    f"{os.path.dirname(get_path())}/charts/resource-pack/values.yaml", "r"
            ) as stream:
                chart_yaml = yaml.safe_load(stream)
                chart_yaml["image"][
                    "repository"
                ] = f"{repository}/{package_name}-container"
                chart_yaml["image"]["tag"] = version
                with open(
                        f"{os.path.dirname(get_path())}/charts/resource-pack/values.yaml",
                        "w",
                ) as stream:
                    yaml.safe_dump(chart_yaml, stream)

            import subprocess

            subprocess.check_call(
                [
                    "helm",
                    "package",
                    f"{os.path.dirname(get_path())}/charts/resource-pack",
                    "--version",
                    version,
                    "--app-version",
                    metadata_obj["version"],
                    "--destination",
                    output,
                ]
            )

            copyfile(
                f"{os.path.dirname(get_path())}/charts/resource-container/Dockerfile",
                os.path.join(output, "Dockerfile"),
            )
            copyfile(
                f"{os.path.dirname(get_path())}/charts/resource-container/health-check.conf",
                os.path.join(output, "health-check.conf"),
            )
            print(
                "\nIn order to make the resource pack available you will need to run the following commands:\n"
            )
            print(f"docker build -t {repository}/{package_name}-container:{version} .")
            print(f"docker push {repository}/{package_name}-container:{version}")

