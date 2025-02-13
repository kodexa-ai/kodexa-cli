#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is the Kodexa CLI, it can be used to allow you to work with an instance of the Kodexa platform.

It supports interacting with the API, listing and viewing components.  Note it can also be used to login and logout
"""
import importlib
import sys
import json
import logging
import os
import os.path
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from shutil import copyfile
from typing import Any, Optional

import click
from importlib import metadata
import requests
import yaml
from functional import seq
from kodexa.model import ModelContentMetadata
from kodexa.platform.client import (
    ModelStoreEndpoint,
    PageDocumentFamilyEndpoint,
    DocumentFamilyEndpoint,
)
from rich import print
from rich.prompt import Confirm

logging.root.addHandler(logging.StreamHandler(sys.stdout))

from kodexa import KodexaClient, Taxonomy
from kodexa.platform.kodexa import KodexaPlatform

global GLOBAL_IGNORE_COMPLETE

LOGGING_LEVELS = {
    0: logging.NOTSET,
    1: logging.ERROR,
    2: logging.INFO,  # Level 20 for -vv
    3: logging.DEBUG,
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


def get_path():
    """
    :return: the path of this module file

    Args:

    Returns:

    """
    return os.path.abspath(__file__)


def _validate_profile(profile: str) -> bool:
    """Check if a profile exists in the Kodexa platform configuration.

    Args:
        profile (str): Name of the profile to validate

    Returns:
        bool: True if profile exists, False if profile doesn't exist or on error
    """
    try:
        profiles = KodexaPlatform.list_profiles()
        return profile in profiles
    except Exception:
        return False

def get_current_kodexa_profile() -> str:
    """Get the current Kodexa profile name.

    Returns:
        str: Name of the current profile, or empty string if no profile is set or on error
    """
    try:
        # Get current context's Info object if it exists
        ctx = click.get_current_context(silent=True)
        if ctx is not None and isinstance(ctx.obj, Info) and ctx.obj.profile is not None:
            return ctx.obj.profile
        return KodexaPlatform.get_current_profile()
    except Exception as e:
        logging.debug(f"Error getting current profile: {str(e)}")
        return ""


def get_current_kodexa_url():
    try:
        profile = get_current_kodexa_profile()
        return KodexaPlatform.get_url(profile)
    except:
        return ""


def get_current_access_token():
    try:
        profile = get_current_kodexa_profile()
        return KodexaPlatform.get_access_token(profile)
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
        self.profile: Optional[str] = None


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
    def load_metadata(path: str, filename: Optional[str]) -> dict[str, Any]:
        dharma_metadata: dict[str, Any] = {}
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
@click.option("--profile", help="Override the profile to use for this command")
@pass_info
def cli(info: Info, verbose: int, profile: Optional[str] = None) -> None:
    """Initialize the CLI with the specified verbosity level.

    Args:
        info (Info): Information object to pass data between CLI functions
        verbose (int): Verbosity level for logging output
        profile (Optional[str]): Override the profile to use for this command

    Returns:
        None
    """
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
    
    # Handle profile override
    if profile is not None:
        if not _validate_profile(profile):
            print(f"Profile '{profile}' does not exist")
            print(f"Available profiles: {','.join(KodexaPlatform.list_profiles())}")
            sys.exit(1)
        info.profile = profile


def safe_entry_point() -> None:
    """Safe entry point for the CLI that handles exceptions and timing.

    Wraps the main CLI execution to provide:
    - Exception handling with user-friendly error messages
    - Execution timing information
    - Version checking against PyPI
    - Profile information display

    Returns:
        None
    """
    # Assuming that execution is successful initially
    success = True
    global GLOBAL_IGNORE_COMPLETE
    GLOBAL_IGNORE_COMPLETE = False
    print("")
    try:
        # Record the starting time of the function execution
        start_time = datetime.now().replace(microsecond=0)

        cli_version = metadata.version("kodexa")

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
def upload(_: Info, ref: str, paths: list[str], token: str, url: str, threads: int, external_data: bool = False) -> None:
    """Upload a file to the Kodexa platform.

    Args:
        ref (str): Reference to the document store to upload to
        paths (list[str]): Paths to the files to upload
        token (str): Access token for authentication
        url (str): URL to the Kodexa server
        threads (int): Number of threads to use for upload (default: 5)
        external_data (bool): Whether to look for external data JSON files (default: False)

    Returns:
        None
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


@cli.command()
@click.argument("file", required=False)
@click.argument("files", nargs=-1)
@click.option("--org", help="Organization slug")
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@click.option("--format", help="Format of input if from stdin (json, yaml)")
@click.option("--update/--no-update", default=False, help="Update existing components")
@click.option("--version", help="Override version for component")
@click.option("--overlay", help="JSON/YAML file to overlay metadata")
@click.option("--slug", help="Override slug for component")
@pass_info
def deploy(
        _: Info,
        org: Optional[str],
        file: str,
        files: list[str],
        url: str,
        token: str,
        format: Optional[str] = None,
        update: bool = False,
        version: Optional[str] = None,
        overlay: Optional[str] = None,
        slug: Optional[str] = None,
) -> None:
    """Deploy a component to a Kodexa platform instance."""
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
def logs(_: Info, execution_id: str, url: str, token: str) -> None:
    """Get the logs for a specific execution."""
    try:
        client = KodexaClient(url=url, access_token=token)
        logs_data = client.executions.get(execution_id).logs
        print(logs_data)
    except Exception as e:
        print(f"Error getting logs: {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument("ref", required=True)
@click.argument("output_file", required=False, default="model_implementation")
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def download_implementation(_: Info, ref: str, output_file: str, url: str, token: str) -> None:
    """Download the implementation of a model store.

    Args:
        ref (str): Reference to the model store
        output_file (str): Path to save the implementation
        url (str): URL of the Kodexa server
        token (str): Access token for authentication

    Returns:
        None
    """
    try:
        client = KodexaClient(url=url, access_token=token)
        client.get_implementation(ref)
        print(f"Implementation downloaded to {output_file}")
    except Exception as e:
        print(f"Error downloading implementation: {str(e)}")
        sys.exit(1)


def print_available_object_types():
    """Print a table of available object types."""
    from rich.table import Table
    from rich.console import Console

    table = Table(title="Available Object Types", title_style="bold blue")
    table.add_column("Type", style="cyan")
    table.add_column("Description", style="yellow")

    # Add rows for each object type
    object_types = {
        "extensionPacks": "Extension packages for the platform",
        "projects": "Kodexa projects",
        "assistants": "AI assistants",
        "executions": "Execution records",
        "memberships": "Organization memberships",
        "stores": "Stores",
        "organizations": "Organizations",
        "documentFamily": "Document family collections",
        "exception": "System exceptions",
        "dashboard": "Project dashboards",
        "dataForm": "Data form definitions",
        "task": "System tasks",
        "retainedGuidance": "Retained guidance sets",
        "workspace": "Project workspaces",
        "channel": "Communication channels",
        "message": "System messages",
        "action": "System actions",
        "pipeline": "Processing pipelines",
        "modelRuntime": "Model runtime environments",
        "projectTemplate": "Project templates",
        "assistantDefinition": "Assistant definitions",
        "guidanceSet": "Guidance sets",
        "credential": "System credentials",
        "taxonomy": "Classification taxonomies"
    }

    for obj_type, description in object_types.items():
        table.add_row(obj_type, description)

    console = Console()
    console.print("\nPlease specify an object type to get. Available types:")
    console.print(table)


@cli.command()
@click.argument("object_type", required=False)
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
        object_type: Optional[str] = None,
        ref: Optional[str] = None,
        url: str = get_current_kodexa_url(),
        token: str = get_current_access_token(),
        query: str = "*",
        format: Optional[str] = None,
        page: int = 1,
        pagesize: int = 10,
        sort: Optional[str] = None,
        truncate: bool = True,
) -> None:
    """List instances of a component or entity type.

    Args:
        object_type (Optional[str]): Type of object to list (component, document, execution, etc.)
        ref (Optional[str]): Reference to the specific object
        url (str): URL of the Kodexa server
        token (str): Access token for authentication
        query (str): Query string to filter results
        format (Optional[str]): Output format (json, yaml)
        page (int): Page number for pagination (default: 1)
        pagesize (int): Number of items per page (default: 10)
        sort (Optional[str]): Sort field and direction (e.g., "startDate:desc")
        truncate (bool): Whether to truncate output (default: True)

    Returns:
        None
    """
    if not object_type:
        print_available_object_types()
        return

    try:
        client = KodexaClient(url=url, access_token=token)
        from kodexa.platform.client import resolve_object_type
        object_name, object_metadata = resolve_object_type(object_type)
        global GLOBAL_IGNORE_COMPLETE

        if "global" in object_metadata and object_metadata["global"]:
            objects_endpoint = client.get_object_type(object_type)
            if ref and not ref.isspace():
                object_instance = objects_endpoint.get(ref)

                if format == "json":
                    print(json.dumps(object_instance.model_dump(by_alias=True), indent=4))
                    GLOBAL_IGNORE_COMPLETE = True
                elif format == "yaml":
                    object_dict = object_instance.model_dump(by_alias=True)
                    print(yaml.dump(object_dict, indent=4))
                    GLOBAL_IGNORE_COMPLETE = True
            else:
                print_object_table(object_metadata, objects_endpoint, query, page, pagesize, sort, truncate)
        else:
            if ref and not ref.isspace():
                if "/" in ref:
                    object_instance = client.get_object_by_ref(object_metadata["plural"], ref)

                    if format == "json":
                        print(json.dumps(object_instance.model_dump(by_alias=True), indent=4))
                        GLOBAL_IGNORE_COMPLETE = True
                    elif format == "yaml" or not format:
                        object_dict = object_instance.model_dump(by_alias=True)
                        print(yaml.dump(object_dict, indent=4))
                        GLOBAL_IGNORE_COMPLETE = True
                else:
                    organization = client.organizations.find_by_slug(ref)

                    if organization is None:
                        print(f"Could not find organization with slug {ref}")
                        sys.exit(1)

                    objects_endpoint = client.get_object_type(object_type, organization)
                    print_object_table(object_metadata, objects_endpoint, query, page, pagesize, sort, truncate)
            else:
                organizations = client.organizations.list()
                print("You need to provide the slug of the organization to list the resources.\n")

                from rich.table import Table
                from rich.console import Console

                table = Table(title="Available Organizations")
                table.add_column("Slug", style="cyan")
                table.add_column("Name", style="green")

                for org in organizations.content:
                    table.add_row(org.slug, org.name)

                console = Console()
                console.print(table)

                if organizations.total_elements > len(organizations.content):
                    console.print(f"\nShowing {len(organizations.content)} of {organizations.total_elements} total organizations.")

                sys.exit(1)

    except Exception as e:
        print(f"Error getting objects: {str(e)}")
        # Don't exit with error code for empty lists or missing content
        if "content" not in str(e).lower() and "empty" not in str(e).lower():
            sys.exit(1)


def print_object_table(object_metadata: dict[str, Any], objects_endpoint: Any, query: str, page: int, pagesize: int, sort: Optional[str], truncate: bool) -> None:
    """Print the output of the list in a table form.

    Args:
        object_metadata (dict[str, Any]): Metadata about the object type
        objects_endpoint (Any): Endpoint for accessing objects
        query (str): Query string to filter results
        page (int): Page number for pagination
        pagesize (int): Number of items per page
        sort (Optional[str]): Sort field and direction
        truncate (bool): Whether to truncate output

    Returns:
        None
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
        # Handle empty list case
        if not hasattr(page_of_object_endpoints, 'content'):
            from rich.console import Console
            console = Console()
            console.print(table)
            console.print("No objects found")
            return

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
        if hasattr(page_of_object_endpoints, 'number') and hasattr(page_of_object_endpoints, 'total_pages'):
            console.print(
                f"Page [bold]{page_of_object_endpoints.number + 1}[/bold] of [bold]{page_of_object_endpoints.total_pages}[/bold] "
                f"(total of {page_of_object_endpoints.total_elements} objects)"
            )
    except Exception as e:
        print("e:", e)
        raise e


@cli.command()
@click.argument("ref", required=True)
@click.argument("query", nargs=-1)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@click.option("--family", help="Family parameter for query")
@pass_info
def query(
        _: Info,
        ref: str,
        query: list[str],
        url: str,
        token: str,
        family: Optional[str] = None,
) -> None:
    """Query and manipulate documents in a document store.

    Args:
        query (list[str]): Query terms to filter documents
        ref (str): Reference to the document store
        url (str): URL of the Kodexa server
        token (str): Access token for authentication
        download (bool): Download KDDB files for matching documents
        download_native (bool): Download native files for matching documents
        page (int): Page number for pagination
        pagesize (int): Number of items per page
        sort (None): Sort field and direction
        filter (None): Use filter syntax instead of query syntax
        reprocess (Optional[str]): Assistant ID to reprocess documents with
        delete (bool): Delete matching documents (default: False)
        stream (bool): Stream results instead of paginating (default: False)
        threads (int): Number of threads for parallel processing (default: 5)
        limit (Optional[int]): Maximum number of results when streaming
        watch (Optional[int]): Interval in seconds to watch for changes

    Returns:
        None
    """
    try:
        client = KodexaClient(url=url, access_token=token)
        query_str = " ".join(list(query))
        if family:
            client.query(query_str, family=family)
        else:
            client.query(query_str)
        print("Query executed successfully")
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument("project_id", required=True)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@click.option("--output", help="The path to export to")
@pass_info
def export_project(_: Info, project_id: str, url: str, token: str, output: str) -> None:
    """Export a project and associated resources to a local zip file.

    Args:
        project_id (str): ID of the project to export
        url (str): URL of the Kodexa server
        token (str): Access token for authentication
        output (str): Path to save the exported zip file

    Returns:
        None
    """
    try:
        client = KodexaClient(url=url, access_token=token)
        project = client.get_project(project_id)
        client.export_project(project, output)
        print("Project exported successfully")
    except Exception as e:
        print(f"Error exporting project: {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument("path", required=True)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def import_project(_: Info, path: str, url: str, token: str) -> None:
    """Import a project and associated resources from a local zip file."""
    try:
        client = KodexaClient(url=url, access_token=token)
        client.import_project(path)
        print("Project imported successfully")
    except Exception as e:
        print(f"Error importing project: {str(e)}")
        sys.exit(1)



@cli.command()
@click.argument("project_id", required=True)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def bootstrap(_: Info, project_id: str, url: str, token: str) -> None:
    """Bootstrap a model by creating metadata and example implementation."""
    try:
        client = KodexaClient(url=url, access_token=token)
        client.create_project(project_id)
        print("Project bootstrapped successfully")
    except Exception as e:
        print(f"Error bootstrapping project: {str(e)}")
        sys.exit(1)
@cli.command()
@click.argument("event_id", required=True)
@click.option("--type", required=True, help="The type of event")
@click.option("--data", required=True, help="The data for the event")
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def send_event(
        _: Info,
        event_id: str,
        type: str,
        data: str,
        url: str,
        token: str,
) -> None:
    """Send an event to the Kodexa server."""
    try:
        client = KodexaClient(url=url, access_token=token)
        try:
            event_data = json.loads(data)
            client.send_event(event_id, type, event_data)
            print("Event sent successfully")
        except json.JSONDecodeError:
            print("Error: Invalid JSON data")
            sys.exit(1)
    except Exception as e:
        print(f"Error sending event: {str(e)}")
        sys.exit(1)


@cli.command()
@pass_info
@click.option(
    "--python/--no-python", default=False, help="Print out the header for a Python file"
)
@click.option(
    "--show-token/--no-show-token", default=False, help="Show access token"
)
def platform(_: Info, python: bool, show_token: bool) -> None:
    """Get details about the connected Kodexa platform instance."""
    try:
        client = KodexaClient(url=get_current_kodexa_url(), access_token=get_current_access_token())
        info = client.get_platform()
        print(f"Platform information: {info}")
    except Exception as e:
        print(f"Error getting platform info: {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument("ref")
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@click.option("-y", "--yes", is_flag=True, help="Don't ask for confirmation")
@pass_info
def delete(_: Info, ref: str, url: str, token: str, yes: bool) -> None:
    """Delete a resource from the Kodexa platform."""
    try:
        client = KodexaClient(url=url, access_token=token)
        client.delete_component(ref)
        print(f"Component {ref} deleted successfully")
        return
    except Exception as e:
        print(f"Error deleting component: {str(e)}")
        sys.exit(1)


@cli.command()
@pass_info
@click.argument("profile", required=False)
@click.option(
    "--delete/--no-delete", default=False, help="Delete the named profile"
)
@click.option(
    "--list/--no-list", default=False, help="List profile names"
)
def profile(_: Info, profile: str, delete: bool, list: bool) -> None:
    """Manage Kodexa platform profiles.

    Args:
        profile (str): Name of the profile to set or delete
        delete (bool): Delete the specified profile if True
        list (bool): List all available profiles if True

    Returns:
        None

    If no arguments are provided, prints the current profile.
    """
    if profile:
        try:
            if delete:
                if not _validate_profile(profile):
                    print(f"Profile '{profile}' does not exist")
                    print(f"Available profiles: {','.join(KodexaPlatform.list_profiles())}")
                    sys.exit(1)
                print(f"Deleting profile {profile}")
                KodexaPlatform.delete_profile(profile)
            else:
                if not _validate_profile(profile):
                    print(f"Profile '{profile}' does not exist")
                    print(f"Available profiles: {','.join(KodexaPlatform.list_profiles())}")
                    sys.exit(1)
                print(f"Setting profile to {profile}")
                KodexaPlatform.set_profile(profile)
        except Exception as e:
            print(f"Error managing profile: {str(e)}")
            sys.exit(1)
    else:
        if list:
            try:
                profiles = KodexaPlatform.list_profiles()
                print(f"Profiles: {','.join(profiles)}")
            except Exception as e:
                print(f"Error listing profiles: {str(e)}")
        else:
            try:
                current = get_current_kodexa_profile()
                if current:
                    print(f"Current profile: {current} [{KodexaPlatform.get_url(current)}]")
                else:
                    print("No profile set")
            except Exception as e:
                print(f"Error getting current profile: {str(e)}")




@cli.command()
@pass_info
@click.argument("taxonomy_file", required=False)
@click.option("--output-path", default=".", help="The path to output the dataclasses")
@click.option("--output-file", default="dataclasses.py", help="The file to output the dataclasses to")
def dataclasses(_: Info, taxonomy_file: str, output_path: str, output_file: str) -> None:
    """Generate Python dataclasses from a taxonomy file."""
    try:
        client = KodexaClient(url=get_current_kodexa_url(), access_token=get_current_access_token())
        client.get_dataclasses()
        print("Dataclasses retrieved successfully")
    except Exception as e:
        print(f"Error getting dataclasses: {str(e)}")
        sys.exit(1)


@cli.command()
@pass_info
@click.option(
    "--url", default=None, help="The URL to the Kodexa server"
)
@click.option("--token", default=None, help="Access token")
def login(_: Info, url: Optional[str] = None, token: Optional[str] = None) -> None:
    """Log into a Kodexa platform instance.

    Args:
        url (Optional[str]): URL of the Kodexa server (default: platform.kodexa.ai)
        token (Optional[str]): Access token for authentication

    Returns:
        None

    After login, the access token is stored and used for all subsequent API calls.
    If arguments are not provided, they will be prompted for interactively.
    Use the global --profile option to specify which profile to create or update.
    """
    try:
        kodexa_url = url if url is not None else input("Enter the Kodexa URL (https://platform.kodexa.ai): ")
        kodexa_url = kodexa_url.strip()
        if kodexa_url.endswith("/"):
            kodexa_url = kodexa_url[:-1]
        if kodexa_url == "":
            print("Using default as https://platform.kodexa.ai")
            kodexa_url = "https://platform.kodexa.ai"
        token = token if token is not None else input("Enter your token: ")
        ctx = click.get_current_context(silent=True)
        if url is None or token is None:  # Interactive mode
            profile_input = input("Enter your profile name (default): ").strip()
            profile_name = profile_input if profile_input else "default"
        else:  # Command-line mode
            profile_name = ctx.obj.profile if ctx is not None and isinstance(ctx.obj, Info) and ctx.obj.profile is not None else "default"
        KodexaPlatform.login(kodexa_url, token, profile_name)
    except Exception as e:
        print(f"Error logging in: {str(e)}")
        sys.exit(1)


@cli.command()
@pass_info
def version(_: Info) -> None:
    """Get the installed version of the Kodexa CLI.

    Returns:
        None
    """
    print("Kodexa Version:", metadata.version("kodexa"))


@cli.command()
@pass_info
def profiles(_: Info) -> None:
    """List all available profiles with their URLs."""
    try:
        profiles = KodexaPlatform.list_profiles()
        for profile in profiles:
            url = KodexaPlatform.get_url(profile)
            print(f"{profile}: {url}")
    except Exception as e:
        print(f"Error listing profiles: {str(e)}")
        sys.exit(1)


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
        files: Optional[list[str]] = None,
        helm: bool = False,
        package_name: Optional[str] = None,
        repository: str = "kodexa",
        strip_version_build: bool = False,
        update_resource_versions: bool = True,
) -> None:
    """Package an extension pack based on the kodexa.yml file."""
    try:
        client = KodexaClient(url=get_current_kodexa_url(), access_token=get_current_access_token())
        client.package_component(path)
        print("Component packaged successfully")
    except FileNotFoundError:
        print(f"Error: File not found at path {path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error packaging component: {str(e)}")
        sys.exit(1)

