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
from kodexa.platform.manifest import ManifestManager

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
import concurrent.futures
import csv
import better_exceptions
import time
better_exceptions.hook()

logging.root.addHandler(logging.StreamHandler(sys.stdout))

from kodexa import KodexaClient, Taxonomy
from kodexa.platform.kodexa import KodexaPlatform

global GLOBAL_IGNORE_COMPLETE

def print_error_message(title: str, message: str, error: Optional[str] = None) -> None:
    """Print a standardized error message using rich formatting.
    
    Args:
        title (str): The title of the error
        message (str): The main error message
        error (Optional[str]): The specific error details
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    
    console = Console()
    
    # Create a styled message
    text = Text()
    text.append("\n⚠️ ", style="bold yellow")
    text.append(title, style="bold red")
    text.append("\n\n")
    text.append(message)
    
    if error:
        text.append("\n\nError details:\n")
        text.append(error, style="dim")
    
    text.append("\n\nFor more information, visit our documentation:")
    text.append("\nhttps://developer.kodexa.ai/guides/cli", style="bold blue")
    
    # Create a panel with the message
    panel = Panel(
        text,
        title="[bold]Kodexa CLI Error[/bold]",
        border_style="red",
        padding=(1, 2)
    )
    
    console.print(panel)

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
    "tasks": ["id", "title", "description", "project.name", "project.organization.name", "status.label"],
    "default": ["ref", "name", "description", "type", "template"],
}


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


def get_path():
    """
    :return: the path of this module file
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
        KodexaPlatform.clear_profile()
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

def config_check(url, token) -> bool:
    if not url or not token:
        from rich.console import Console
        from rich.panel import Panel
        from rich.markdown import Markdown
        from rich.text import Text
        
        console = Console()
        
        # Create a styled message
        message = Text()
        message.append("\n🔐 ", style="bold yellow")
        message.append("Authentication Required", style="bold red")
        message.append("\n\nYour Kodexa profile is not configured or is misconfigured.")
        message.append("\n\nTo proceed, you need to authenticate with the Kodexa platform.")
        message.append("\n\nRun the following command to login:")
        message.append("\n\n", style="bold")
        message.append("kodexa login", style="bold green")
        message.append("\n\nFor more information, visit our documentation:")
        message.append("\n", style="bold")
        message.append("https://developer.kodexa.ai/guides/cli/authentication", style="bold blue")
        
        # Create a panel with the message
        panel = Panel(
            message,
            title="[bold]Kodexa CLI Authentication[/bold]",
            border_style="blue",
            padding=(1, 2)
        )
        
        console.print(panel)
        return False
    return True



@contextmanager
def set_directory(path: Path):
    """Sets the cwd within the context
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

        try:
            current_kodexa_profile = get_current_kodexa_profile()
            current_kodexa_url = get_current_kodexa_url()
            if current_kodexa_profile and current_kodexa_url:
                print(f"Using profile {current_kodexa_profile} @ {current_kodexa_url}\n")
        except Exception as e:
            print_error_message(
                "Profile Error",
                "Unable to load your Kodexa profile.",
                str(e)
            )

        # Call the cli() function
        cli()
    except Exception as e:
        # If an exception occurs, mark success as False and print the exception
        success = False
        print_error_message(
            "Command Failed",
            "The command could not be completed successfully.",
            str(e)
        )
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
@click.argument("object_type", required=False)
@click.argument("ref", required=False)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@click.option("--query", default="*", help="Limit the results using a query")
@click.option("--filter/--no-filter", default=False, help="Switch from query to filter syntax")
@click.option("--format", default=None, help="The format to output (json, yaml)")
@click.option("--page", default=1, help="Page number")
@click.option("--pageSize", default=10, help="Page size")
@click.option("--sort", default=None, help="Sort by (ie. startDate:desc)")
@click.option("--truncate/--no-truncate", default=True, help="Truncate the output or not")
@click.option("--stream/--no-stream", default=False, help="Stream results instead of using table output")
@click.option("--delete/--no-delete", default=False, help="Delete streamed objects")
@click.option("--output-path", default=None, help="Output directory to save the results")
@click.option("--output-file", default=None, help="Output file to save the results")
@pass_info
def get(
        _: Info,
        object_type: Optional[str] = None,
        ref: Optional[str] = None,
        url: str = get_current_kodexa_url(),
        token: str = get_current_access_token(),
        query: str = "*",
        filter: bool = False,
        format: Optional[str] = None,
        page: int = 1,
        pagesize: int = 10,
        sort: Optional[str] = None,
        truncate: bool = True,
        stream: bool = False,
        delete: bool = False,
        output_path: Optional[str] = None,
        output_file: Optional[str] = None
) -> None:
    """List or retrieve Kodexa platform objects.
    
    This command allows you to query and retrieve various types of objects from the Kodexa platform,
    including assistants, stores, projects, organizations, and more.
    
    Arguments:
        OBJECT_TYPE: The type of object to retrieve (e.g., 'assistants', 'stores', 'projects')
        REF: Optional reference ID or slug to get a specific object
    
    Examples:
        # List all assistants
        kodexa get assistants
        
        # Get a specific project by ref
        kodexa get projects my-org/my-project
        
        # Query stores with filtering
        kodexa get stores --query "name:*test*"
        
        # Stream and delete matching objects (use with caution)
        kodexa get documentFamily my-org --stream --delete
        
        # Export results to a file
        kodexa get assistants --output-file assistants.json --format json
    """

    if not config_check(url, token):
        return

    if not object_type:
        print_available_object_types()
        return
    
    

    # Handle file output setup
    def save_to_file(data, output_format=None):
        if output_file is None:
            return False
        
        # Determine the full file path
        file_path = output_file
        if output_path:
            os.makedirs(output_path, exist_ok=True)
            file_path = os.path.join(output_path, output_file)
        
        # Determine format based on file extension if not specified
        if output_format is None:
            if file_path.lower().endswith('.json'):
                output_format = 'json'
            elif file_path.lower().endswith(('.yaml', '.yml')):
                output_format = 'yaml'
            else:
                output_format = format or 'json'  # Default to json if no extension hint
        
        # Write data to file in appropriate format
        with open(file_path, 'w') as f:
            # Check if data is a pydantic object and convert it to dict if needed
            if hasattr(data, 'model_dump'):
                data_to_write = data.model_dump(by_alias=True)
            elif hasattr(data, 'dict'):  # For older pydantic versions
                data_to_write = data.dict(by_alias=True)
            else:
                data_to_write = data
                
            if output_format == 'json':
                json.dump(data_to_write, f, indent=4)
            else:  # yaml
                yaml.dump(data_to_write, f, indent=4)
        
        print(f"Output written to {file_path}")
        return True

    try:
        client = KodexaClient(url=url, access_token=token)
        from kodexa.platform.client import resolve_object_type
        object_name, object_metadata = resolve_object_type(object_type)
        global GLOBAL_IGNORE_COMPLETE

        if "global" in object_metadata and object_metadata["global"]:
            objects_endpoint = client.get_object_type(object_type)
            if ref and not ref.isspace():
                object_instance = objects_endpoint.get(ref)
                object_dict = object_instance.model_dump(by_alias=True)
                
                # Save to file if output_file is specified
                if output_file and save_to_file(object_dict, format):
                    GLOBAL_IGNORE_COMPLETE = True
                    return
                # Check if data is a pydantic object and convert it to dict if needed
                if hasattr(object_instance, 'model_dump'):
                    data_to_print = object_instance.model_dump(by_alias=True)
                elif hasattr(object_instance, 'dict'):  # For older pydantic versions
                    data_to_print = object_instance.dict(by_alias=True)
                else:
                    data_to_print = object_dict
                
                if format == "json":
                    # Check if data is a pydantic object and convert it to dict if needed
                    if hasattr(data_to_print, 'model_dump'):
                        data_to_print = data_to_print.model_dump(by_alias=True)
                    elif hasattr(data_to_print, 'dict'):  # For older pydantic versions
                        data_to_print = data_to_print.dict(by_alias=True)
                    print(json.dumps(data_to_print, indent=4))
                    GLOBAL_IGNORE_COMPLETE = True
                elif format == "yaml":
                    # Check if data is a pydantic object and convert it to dict if needed
                    if hasattr(data_to_print, 'model_dump'):
                        data_to_print = data_to_print.model_dump(by_alias=True)
                    elif hasattr(data_to_print, 'dict'):  # For older pydantic versions
                        data_to_print = data_to_print.dict(by_alias=True)
                    print(yaml.dump(data_to_print, indent=4))
                    GLOBAL_IGNORE_COMPLETE = True
            else:
                if stream:
                    if filter:
                        print(f"Streaming filter: {query}\n")
                        all_objects = objects_endpoint.stream(filters=[query], sort=sort)
                    else:
                        print(f"Streaming query: {query}\n")
                        all_objects = objects_endpoint.stream(query=query, sort=sort)

                    if delete and not Confirm.ask(
                            "Are you sure you want to delete these objects? This action cannot be undone."
                    ):
                        print("Aborting delete")
                        exit(1)

                    # Collect objects for file output if needed
                    collected_objects = []
                    if output_file:
                        for obj in all_objects:
                            try:
                                if delete:
                                    obj.delete()
                                    print(f"Deleted {obj.id}")
                                else:
                                    collected_objects.append(obj.model_dump(by_alias=True))
                                    print(f"Processing {obj.id}")
                            except Exception as e:
                                print(f"Error processing {obj.id}: {e}")
                        
                        if collected_objects and save_to_file(collected_objects, format):
                            GLOBAL_IGNORE_COMPLETE = True
                            return
                    else:
                        for obj in all_objects:
                            try:
                                print(f"Processing {obj.id}")
                                if delete:
                                    obj.delete()
                                    print(f"Deleted {obj.id}")
                                else:
                                    print(obj)
                            except Exception as e:
                                print(f"Error processing {obj.id}: {e}")
                else:
                    if filter:
                        print(f"Using filter: {query}\n")
                        objects_endpoint_page = objects_endpoint.list("*", page, pagesize, sort, filters=[query])
                    else:
                        print(f"Using query: {query}\n")
                        objects_endpoint_page = objects_endpoint.list(query=query, page=page, page_size=pagesize,
                                                                     sort=sort)
                    
                    # Save to file if output_file is specified
                    if output_file and hasattr(objects_endpoint_page, 'content'):
                        collection_data = [obj.model_dump(by_alias=True) for obj in objects_endpoint_page.content]
                        page_data = {
                            "content": collection_data,
                            "page": objects_endpoint_page.number,
                            "pageSize": objects_endpoint_page.size,
                            "totalPages": objects_endpoint_page.total_pages,
                            "totalElements": objects_endpoint_page.total_elements
                        }
                        if save_to_file(page_data, format):
                            GLOBAL_IGNORE_COMPLETE = True
                            return
                    
                    print_object_table(object_metadata, objects_endpoint_page, query, page, pagesize, sort, truncate)
        else:
            if ref and not ref.isspace():
                if "/" in ref:
                    object_instance = client.get_object_by_ref(object_metadata["plural"], ref)
                    object_dict = object_instance.model_dump(by_alias=True)
                    
                    # Save to file if output_file is specified
                    if output_file and save_to_file(object_dict, format):
                        GLOBAL_IGNORE_COMPLETE = True
                        return
                    
                    if format == "json":
                        # Handle both regular dict and pydantic objects
                        if hasattr(object_instance, 'model_dump'):
                            print(json.dumps(object_instance.model_dump(by_alias=True), indent=4))
                        elif hasattr(object_instance, 'dict'):  # For older pydantic versions
                            print(json.dumps(object_instance.dict(by_alias=True), indent=4))
                        else:
                            print(json.dumps(object_dict, indent=4))
                        GLOBAL_IGNORE_COMPLETE = True
                    elif format == "yaml" or not format:
                        # Handle both regular dict and pydantic objects
                        if hasattr(object_instance, 'model_dump'):
                            print(yaml.dump(object_instance.model_dump(by_alias=True), indent=4))
                        elif hasattr(object_instance, 'dict'):  # For older pydantic versions
                            print(yaml.dump(object_instance.dict(by_alias=True), indent=4))
                        else:
                            print(yaml.dump(object_dict, indent=4))
                        GLOBAL_IGNORE_COMPLETE = True
                else:
                    organization = client.organizations.find_by_slug(ref)

                    if organization is None:
                        print(f"Could not find organization with slug {ref}")
                        sys.exit(1)

                    objects_endpoint = client.get_object_type(object_type, organization)
                    if stream:
                        if filter:
                            all_objects = objects_endpoint.stream(filters=[query], sort=sort)
                        else:
                            all_objects = objects_endpoint.stream(query=query, sort=sort)

                        if delete and not Confirm.ask(
                                "Are you sure you want to delete these objects? This action cannot be undone."
                        ):
                            print("Aborting delete")
                            exit(1)

                        # Collect objects for file output if needed
                        collected_objects = []
                        if output_file:
                            for obj in all_objects:
                                try:
                                    if delete:
                                        obj.delete()
                                        print(f"Deleted {obj.id}")
                                    else:
                                        collected_objects.append(obj.model_dump(by_alias=True))
                                        print(f"Processing {obj.id}")
                                except Exception as e:
                                    print(f"Error processing {obj.id}: {e}")
                            
                            if collected_objects and save_to_file(collected_objects, format):
                                GLOBAL_IGNORE_COMPLETE = True
                                return
                        else:
                            for obj in all_objects:
                                try:
                                    print(f"Processing {obj.id}")
                                    if delete:
                                        obj.delete()
                                        print(f"Deleted {obj.id}")
                                    else:
                                        # Get column list for the referenced object
                                        if object_metadata["plural"] in DEFAULT_COLUMNS:
                                            column_list = DEFAULT_COLUMNS[object_metadata["plural"]]
                                        else:
                                            column_list = DEFAULT_COLUMNS["default"]

                                        # Print values for each column
                                        values = []
                                        for col in column_list:
                                            try:
                                                # Handle dot notation by splitting and traversing
                                                parts = col.split('.')
                                                value = obj
                                                for part in parts:
                                                    value = getattr(value, part)
                                                values.append(str(value))
                                            except AttributeError:
                                                values.append("")
                                        print(" | ".join(values))
                                except Exception as e:
                                    print(f"Error processing {obj.id}: {e}")
                    else:
                        if filter:
                            print(f"Using filter: {query}\n")
                            objects_endpoint_page = objects_endpoint.filter(query, page, pagesize, sort)
                        else:
                            print(f"Using query: {query}\n")
                            objects_endpoint_page = objects_endpoint.list(query=query, page=page, page_size=pagesize,
                                                                     sort=sort)
                        
                        # Save to file if output_file is specified
                        if output_file and hasattr(objects_endpoint_page, 'content'):
                            collection_data = [obj.model_dump(by_alias=True) for obj in objects_endpoint_page.content]
                            page_data = {
                                "content": collection_data,
                                "page": objects_endpoint_page.number,
                                "pageSize": objects_endpoint_page.size,
                                "totalPages": objects_endpoint_page.total_pages,
                                "totalElements": objects_endpoint_page.total_elements
                            }
                            if save_to_file(page_data, format):
                                GLOBAL_IGNORE_COMPLETE = True
                                return
                        
                        print_object_table(object_metadata, objects_endpoint_page, query, page, pagesize, sort, truncate)
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
                    console.print(
                        f"\nShowing {len(organizations.content)} of {organizations.total_elements} total organizations.")

                sys.exit(1)
    except Exception as e:
        # Print the exception using Better Exceptions
        import better_exceptions
        better_exceptions.hook()
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        # Don't exit with error code for empty lists or missing content
        if "content" not in str(e).lower() and "empty" not in str(e).lower():
            sys.exit(1)


def print_object_table(object_metadata: dict[str, Any], objects_endpoint_page: Any, query: str, page: int,
                       pagesize: int,
                       sort: Optional[str], truncate: bool) -> None:
    """Print the output of the list in a table form.

    Args:
        object_metadata (dict[str, Any]): Metadata about the object type
        objects_endpoint_page (Any): Endpoint for accessing objects
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
        if not hasattr(objects_endpoint_page, 'content'):
            from rich.console import Console
            console = Console()
            console.print(table)
            console.print("No objects found")
            return

        # Get column values
        for objects_endpoint in objects_endpoint_page.content:
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
                        # Handle dot notation by splitting the column name and traversing the object
                        parts = col.split('.')
                        value = objects_endpoint
                        for part in parts:
                            value = getattr(value, part)
                        row.append(str(value))
                    except AttributeError:
                        row.append("")
            table.add_row(*row, style="yellow")

        from rich.console import Console

        console = Console()
        console.print(table)
        console.print(
            f"Page [bold]{objects_endpoint_page.number + 1}[/bold] of [bold]{objects_endpoint_page.total_pages}[/bold] "
            f"(total of {objects_endpoint_page.total_elements} objects)"
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
@click.option(
    "--download-extracted-data/--no-download-extracted-data", default=False, help="Download the extracted data for the matching document families"
)
@click.option(
    "--project-id", default=None, help="The project ID to use for the extracted data"
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
    "--starting-offset", default=None, help="Starting offset for the streaming query", type=int
)
@click.option(
    "--reprocess", default=None, help="Reprocess using the provided assistant ID"
)
@click.option("--add-label", default=None, help="Add a label to the matching document families")
@click.option("--remove-label", default=None, help="Remove a label from the matching document families")
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
        download_extracted_data: bool,
        page: int,
        pagesize: int,
        sort: None,
        filter: None,
        reprocess: Optional[str] = None,
        add_label: Optional[str] = None,
        starting_offset: Optional[int] = None,
        remove_label: Optional[str] = None,
        delete: bool = False,
        stream: bool = False,
        threads: int = 5,
        limit: Optional[int] = None,
        watch: Optional[int] = None,
        project_id: Optional[str] = None,
) -> None:
    """Query and manipulate documents in a document store.
    
    This powerful command allows you to search, download, modify, and manage documents
    within a Kodexa document store. Supports batch operations and streaming for large datasets.
    
    Arguments:
        REF: The reference to the document store (e.g., 'org-slug/store-slug')
        QUERY: Optional query string to filter documents (default: '*' for all)
    
    Examples:
        # List all documents in a store
        kodexa query my-org/my-store
        
        # Search for specific documents
        kodexa query my-org/my-store "invoice*.pdf"
        
        # Download documents matching a query
        kodexa query my-org/my-store "type:invoice" --download
        
        # Reprocess documents with a specific assistant
        kodexa query my-org/my-store --stream --reprocess assistant-id
        
        # Add labels to matching documents
        kodexa query my-org/my-store "status:pending" --add-label reviewed
        
        # Stream and delete documents (use with caution!)
        kodexa query my-org/my-store "created:<2023-01-01" --stream --delete
        
        # Watch for new documents (refresh every 10 seconds)
        kodexa query my-org/my-store --watch 10
    """
    if not config_check(url, token):
        return
    
    client = KodexaClient(url=url, access_token=token)
    from kodexa.platform.client import DocumentStoreEndpoint

    query_str: str = " ".join(list(query)) if query else "*" if not filter else ""

    document_store: DocumentStoreEndpoint = client.get_object_by_ref("store", ref)

    while True:
        if isinstance(document_store, DocumentStoreEndpoint):
            if stream:
                if filter:
                    print(f"Streaming filter: {query_str}\n")
                    page_of_document_families = document_store.stream_filter(
                        query_str, sort, limit, threads, starting_offset=starting_offset if starting_offset else 0
                    )
                else:
                    print(f"Streaming query: {query_str}\n")
                    page_of_document_families = document_store.stream_query(
                        query_str, sort, limit, threads, starting_offset=starting_offset if starting_offset else 0
                    )
            else:
                if filter:
                    print(f"Using filter: {query_str}\n")
                    page_of_document_families: PageDocumentFamilyEndpoint = (
                        document_store.filter(query_str, page, pagesize, sort)
                    )
                else:
                    print(f"Using query: {query_str}\n")
                    page_of_document_families: PageDocumentFamilyEndpoint = (
                        document_store.query(query_str, page, pagesize, sort)
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
                
                if not stream:
                        print("You can't reprocess without streaming")
                        exit(1)
                
                if reprocess.lower() == "failed":
                    print("We will reprocess the document with first failed assistant")
                    assistant = "failed"
                
                else:
                    # We need to get the assistant so we can reprocess
                    assistant = client.assistants.get(reprocess)
                    if assistant is None:
                        print(f"Unable to find assistant with id {reprocess}")
                        exit(1)

                    
                print(f"Reprocessing with assistant {assistant.name if assistant != 'failed' else 'last failed assistant'}")
            
            if stream:
                print(f"Streaming document families (with {threads} threads)")
            
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=threads
            ) as executor:
                def process_family(args) -> None:
                    idx, df = args
                    doc_family: DocumentFamilyEndpoint = df
                    position = starting_offset + idx + 1 if starting_offset else idx + 1
                    if download:
                        print(f"Downloading document for {doc_family.path} (position {position})")
                        doc_family.get_document().to_kddb(doc_family.path + ".kddb")

                    if download_native:
                        print(
                            f"Downloading native object for {doc_family.path} (position {position})"
                        )
                        with open(doc_family.path + ".native", "wb") as f:
                            f.write(doc_family.get_native())
                            
                    if download_extracted_data:
                        if Path(doc_family.path + "-extracted_data.json").exists():
                            print(f"Extracted data already exists for {doc_family.path} (position {position})")
                        else:
                            print(f"Downloading extracted data for {doc_family.path} (position {position})")
                            # Retry logic for downloading and writing extracted data
                            max_retries = 3
                            retry_delay = 2  # seconds
                            
                            for attempt in range(max_retries):
                                try:
                                    # Get the JSON data
                                    json_data = doc_family.get_json(
                                        project_id=project_id, 
                                        friendly_names=False, 
                                        include_ids=True, 
                                        include_exceptions=True, 
                                        inline_audits=False
                                    )
                                    
                                    # Write the JSON file with the extracted data
                                    with open(doc_family.path + "-extracted_data.json", "w") as f:
                                        f.write(json_data)
                                    
                                    # Success - break out of retry loop
                                    break
                                    
                                except Exception as e:
                                    if attempt < max_retries - 1:
                                        print(f"  Retry {attempt + 1}/{max_retries} failed for {doc_family.path}: {str(e)}")
                                        print(f"  Waiting {retry_delay} seconds before retrying...")
                                        time.sleep(retry_delay)
                                    else:
                                        print(f"  Failed to download extracted data for {doc_family.path} after {max_retries} attempts: {str(e)}")
                                        raise

                    if delete:
                        print(f"Deleting {doc_family.path} (position {position})")
                        doc_family.delete()

                    if reprocess is not None:
                        print(f"Reprocessing {doc_family.path} (position {position})")
                        if assistant == "failed":
                            if doc_family.statistics.recent_executions is None:
                                print(f"Skipping reprocessing {doc_family.path} (position {position}) because it has no recent executions")
                            else:
                                for execution in doc_family.statistics.recent_executions:
                                    if execution.execution.status == "FAILED":
                                        print(f"Reprocessing {doc_family.path} (position {position}) with failed assistant {execution.assistant.name}")
                                        doc_family.reprocess(execution.assistant)
                                        break
                        else:
                            doc_family.reprocess(assistant)

                    if add_label is not None:
                        print(f"Adding label {add_label} to {doc_family.path} (position {position})")
                        doc_family.add_label(add_label)

                    if remove_label is not None:
                        print(f"Removing label {remove_label} from {doc_family.path} (position {position})")
                        doc_family.remove_label(remove_label)
                
                # Use enumerate to pass index along with doc_family
                executor.map(process_family, enumerate(document_families))                    

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
def export_project(_: Info, project_id: str, url: str, token: str, output: str) -> None:
    """Export a project and associated resources to a local zip file.
    
    Downloads a complete project including all its configurations, assistants,
    stores, and other resources as a portable zip archive that can be imported
    into another Kodexa instance.
    
    Arguments:
        PROJECT_ID: The ID of the project to export (e.g., 'org-slug/project-slug')
    
    Examples:
        # Export project to current directory
        kodexa export-project my-org/my-project
        
        # Export to specific file
        kodexa export-project my-org/my-project --output /path/to/backup.zip
    """
    if not config_check(url, token):
        return

    try:
        client = KodexaClient(url=url, access_token=token)
        project = client.get_project(project_id)
        client.export_project(project, output)
        print("Project exported successfully")
    except Exception as e:
        print_error_message(
            "Export Failed",
            f"Could not export project {project_id}.",
            str(e)
        )
        sys.exit(1)


@cli.command()
@click.argument("path", required=True)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def import_project(_: Info, path: str, url: str, token: str) -> None:
    """Import a project and associated resources from a local zip file.
    
    Restores a previously exported project including all its configurations,
    assistants, stores, and other resources from a zip archive.
    
    Arguments:
        PATH: Path to the zip file containing the exported project
    
    Examples:
        # Import a project backup
        kodexa import-project /path/to/project-backup.zip
        
        # Import to a different Kodexa instance
        kodexa import-project backup.zip --url https://other.kodexa.ai
    """
    try:
        client = KodexaClient(url=url, access_token=token)
        client.import_project(path)
        print("Project imported successfully")
    except Exception as e:
        print_error_message(
            "Import Failed",
            f"Could not import project from {path}.",
            str(e)
        )
        sys.exit(1)


@cli.command()
@click.argument("project_id", required=True)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def bootstrap(_: Info, project_id: str, url: str, token: str) -> None:
    """Bootstrap a new project with default structure and configuration.
    
    Creates a new project with example metadata, configurations, and a basic
    implementation structure to help you get started quickly.
    
    Arguments:
        PROJECT_ID: The ID for the new project (e.g., 'org-slug/project-slug')
    
    Examples:
        # Bootstrap a new project
        kodexa bootstrap my-org/new-project
        
        # Bootstrap with specific profile
        kodexa bootstrap my-org/ml-project --profile dev
    """
    
    if not config_check(url, token):
        return

    try:
        client = KodexaClient(url=url, access_token=token)
        client.create_project(project_id)
        print("Project bootstrapped successfully")
    except Exception as e:
        print_error_message(
            "Bootstrap Failed",
            f"Could not bootstrap project {project_id}.",
            str(e)
        )
        sys.exit(1)


@cli.command()
@click.argument("manifest_path", required=True)
@click.argument("command", type=click.Choice(["deploy", "undeploy", "sync"]), default="deploy")
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def manifest(
        _: Info,
        manifest_path: str,
        command: str,
        url: str,
        token: str,
) -> None:
    """Manage Kodexa manifests for infrastructure as code.
    
    Manifests allow you to define and manage entire Kodexa environments
    declaratively. You can deploy, update, or remove resources in bulk.
    
    Arguments:
        MANIFEST_PATH: Path to the manifest file
        COMMAND: Operation to perform (deploy/undeploy/sync)
    
    Commands:
        deploy: Create or update resources defined in the manifest
        undeploy: Remove all resources defined in the manifest
        sync: Synchronize local manifest with remote state
    
    Examples:
        # Deploy a manifest (default command)
        kodexa manifest production.yaml
        
        # Explicitly deploy
        kodexa manifest staging.yaml deploy
        
        # Remove all resources in manifest
        kodexa manifest old-env.yaml undeploy
        
        # Sync manifest with current platform state
        kodexa manifest current.yaml sync
    """

    if not config_check(url, token):
        return

    try:
        client = KodexaClient(url=url, access_token=token)
        manifest_manager = ManifestManager(client)
        
        if command == "deploy":
            manifest_manager.deploy_from_manifest(manifest_path)
        elif command == "undeploy":
            manifest_manager.undeploy_from_manifest(manifest_path)
        elif command == "sync":
            manifest_manager.sync_from_instance(manifest_path)
    except Exception as e:
        print(f"Error processing manifest: {str(e)}")
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
    """Send a custom event to the Kodexa platform.
    
    Triggers custom events for workflow automation, notifications,
    or integration with external systems.
    
    Arguments:
        EVENT_ID: Unique identifier for the event
    
    Examples:
        # Send a simple event
        kodexa send-event evt-123 --type notification --data '{"message":"Processing complete"}'
        
        # Send workflow trigger event
        kodexa send-event workflow-001 --type trigger --data '{"action":"start","params":{}}'
        
        # Send integration event
        kodexa send-event integration-xyz --type webhook --data '{"url":"https://api.example.com"}'
    """

    if not config_check(url, token):
        return

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
    """Display information about the connected Kodexa platform.
    
    Shows details about the current Kodexa instance including version,
    capabilities, and connection information.
    
    Examples:
        # Show platform information
        kodexa platform
        
        # Show with Python header format
        kodexa platform --python
        
        # Include access token (careful with security)
        kodexa platform --show-token
    """
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from datetime import datetime
    import re

    try:
        console = Console()
        
        # Get platform information
        client = KodexaClient(url=get_current_kodexa_url(), access_token=get_current_access_token())
        info = client.get("/api/overview").json()
        
        # Create header panel with platform name and release
        header_text = Text()
        platform_name = info.get('name', 'Kodexa')
        release_name = info.get('release', '')
        if release_name:
            header_text.append(f"{platform_name} Platform - {release_name} Release\n", style="bold cyan")
        else:
            header_text.append(f"{platform_name} Platform\n", style="bold cyan")
        header_text.append(f"URL: ", style="white")
        header_text.append(f"{get_current_kodexa_url()}\n", style="green")
        
        if show_token:
            header_text.append(f"Token: ", style="white")
            header_text.append(f"{get_current_access_token()[:20]}...\n", style="yellow")
        
        header_panel = Panel(
            header_text,
            title="[bold]Platform Connection[/bold]",
            border_style="blue"
        )
        console.print(header_panel)
        
        # Create main information table
        table = Table(title="Platform Details", title_style="bold blue", show_header=True)
        table.add_column("Property", style="cyan", width=25)
        table.add_column("Value", style="white", width=100)
        
        # Add version information
        table.add_row("Version", info.get('version', 'N/A'))
        table.add_row("Environment", info.get('environment', 'N/A'))
        
        # Add build information
        table.add_row("Build Time", info.get('buildTime', 'N/A'))
        table.add_row("Commit ID", info.get('commitId', 'N/A'))
        
        # Add client version recommendation
        rec_version = info.get('recommendedClientVersion', 'N/A')
        table.add_row("Recommended Client", rec_version)
        
        # Display raw JSON if python flag is set
        if python:
            console.print("\n[bold cyan]Raw Response (Python dict):[/bold cyan]")
            console.print(info)
            
    except Exception as e:
        console = Console()
        error_panel = Panel(
            f"[red]Error getting platform info:[/red]\n{str(e)}",
            title="[bold]Platform Error[/bold]",
            border_style="red",
            padding=(1, 2)
        )
        console.print(error_panel)
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
    """Delete a resource from the Kodexa platform.
    
    Permanently removes a resource (assistant, store, project, etc.) from the platform.
    This action cannot be undone.
    
    Arguments:
        REF: The reference to the resource to delete (e.g., 'org/resource-slug')
    
    Examples:
        # Delete with confirmation prompt
        kodexa delete my-org/old-assistant
        
        # Delete without confirmation (use with caution!)
        kodexa delete my-org/test-store --yes
    """
    if not config_check(url, token):
        return

    try:
        client = KodexaClient(url=url, access_token=token)
        client.get_object_by_ref(ref).delete()
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
    
    Profiles allow you to maintain multiple sets of credentials for different
    Kodexa instances or environments. You can switch between profiles to work
    with different servers without re-authenticating each time.
    
    Arguments:
        PROFILE: Optional name of the profile to set or delete
    
    Examples:
        # Show current profile
        kodexa profile
        
        # List all profiles
        kodexa profile --list
        
        # Switch to a different profile
        kodexa profile production
        
        # Delete a profile
        kodexa profile old-dev --delete
        
        # Create and use a profile in other commands
        kodexa --profile staging login
        kodexa --profile staging get projects
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
@click.option("--output-file", default="data_classes.py", help="The file to output the dataclasses to")
def dataclasses(_: Info, taxonomy_file: str, output_path: str, output_file: str) -> None:
    """Generate Python dataclasses from a taxonomy definition.
    
    Converts Kodexa taxonomy definitions (JSON/YAML) into Python dataclass
    code for type-safe data extraction and processing.
    
    Arguments:
        TAXONOMY_FILE: Path to the taxonomy file (JSON or YAML)
    
    Examples:
        # Generate dataclasses from taxonomy
        kodexa dataclasses taxonomy.json
        
        # Output to specific location
        kodexa dataclasses taxonomy.yaml --output-path src/models
        
        # Custom output filename
        kodexa dataclasses taxonomy.json --output-file invoice_models.py
    """
    if taxonomy_file is None:
        print("You must provide a taxonomy file")
        exit(1)

    with open(taxonomy_file, "r", encoding="utf-8") as f:

        if taxonomy_file.endswith(".json"):
            taxonomy = json.load(f)
        else:
            taxonomy = yaml.safe_load(f)

    taxonomy = Taxonomy(**taxonomy)

    from kodexa.dataclasses import build_llm_data_classes_for_taxonomy
    build_llm_data_classes_for_taxonomy(taxonomy, output_path, output_file)


@cli.command()
@pass_info
@click.option(
    "--url", default=None, help="The URL to the Kodexa server"
)
@click.option("--token", default=None, help="Access token")
def login(_: Info, url: Optional[str] = None, token: Optional[str] = None) -> None:
    """Log into a Kodexa platform instance.
    
    Authenticates with a Kodexa platform instance and stores credentials for future use.
    Supports multiple profiles for managing different environments (dev, staging, prod).
    
    If URL and token are not provided as options, you'll be prompted interactively.
    The default URL is https://platform.kodexa.ai if not specified.
    
    Examples:
        # Interactive login (recommended for security)
        kodexa login
        
        # Login with parameters
        kodexa login --url https://platform.kodexa.ai --token YOUR_TOKEN
        
        # Create a named profile
        kodexa --profile dev login
        
        # Login to custom instance
        kodexa login --url https://my-kodexa.company.com --token TOKEN
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
            profile_name = ctx.obj.profile if ctx is not None and isinstance(ctx.obj,
                                                                             Info) and ctx.obj.profile is not None else "default"
        KodexaPlatform.login(kodexa_url, token, profile_name)
    except Exception as e:
        print(f"Error logging in: {str(e)}")
        sys.exit(1)


@cli.command()
@pass_info
def version(_: Info) -> None:
    """Display the installed version of Kodexa CLI and libraries.
    
    Shows version information for the Kodexa CLI and related packages.
    Useful for troubleshooting and ensuring compatibility.
    
    Examples:
        # Show version
        kodexa version
    """
    print("Kodexa Version:", metadata.version("kodexa"))


@cli.command()
@pass_info
def profiles(_: Info) -> None:
    """List all configured Kodexa profiles.
    
    Displays all available profiles with their associated Kodexa instance URLs.
    This is useful for seeing which environments you have configured.
    
    Examples:
        # List all profiles
        kodexa profiles
        
    Output format:
        profile-name: https://instance-url.kodexa.ai
    """
    try:
        profiles = KodexaPlatform.list_profiles()
        if not profiles:
            print("No profiles found")
            return

        for profile in profiles:
            url = KodexaPlatform.get_url(profile)
            print(f"{profile}: {url}")
    except Exception as e:
        print_error_message(
            "Profile Error",
            "Could not list profiles.",
            str(e)
        )
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
    """Package Kodexa components for deployment.
    
    Creates deployment packages from kodexa.yml definitions, including support
    for extension packs, model stores, and other component types. Can generate
    Helm charts for Kubernetes deployments.
    
    Arguments:
        FILES: Optional list of kodexa.yml files to package (default: kodexa.yml)
    
    Examples:
        # Package current directory's kodexa.yml
        kodexa package
        
        # Package with specific version
        kodexa package --version 2.1.0
        
        # Package multiple components
        kodexa package assistant.yml model.yml store.yml
        
        # Generate Helm chart for Kubernetes
        kodexa package --helm --package-name my-app --version 1.0.0
        
        # Package to specific output directory
        kodexa package --output /builds/latest
        
        # Strip build number from version
        kodexa package --version 1.0.0-build123 --strip-version-build
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
def upload(_: Info, ref: str, paths: list[str], token: str, url: str, threads: int,
           external_data: bool = False) -> None:
    """Upload files to a document store.
    
    Uploads one or more files to a specified document store for processing.
    Supports parallel uploads for better performance with large file sets.
    
    Arguments:
        REF: Reference to the target document store (e.g., 'org-slug/store-slug')
        PATHS: One or more file paths to upload
    
    Examples:
        # Upload a single file
        kodexa upload my-org/my-store document.pdf
        
        # Upload multiple files
        kodexa upload my-org/my-store *.pdf *.docx
        
        # Upload with external metadata
        kodexa upload my-org/my-store invoice.pdf --external-data
        # (looks for invoice.json with metadata)
        
        # Upload with multiple threads for speed
        kodexa upload my-org/my-store /path/to/files/* --threads 10
        
        # Upload all PDFs in a directory
        kodexa upload my-org/documents ~/Documents/*.pdf
    """

    if not config_check(url, token):
        return

    try:
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
    except Exception as e:
        print_error_message(
            "Upload Failed",
            f"Could not upload files to {ref}.",
            str(e)
        )
        sys.exit(1)


@cli.command()
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
        files: list[str],
        url: str,
        token: str,
        format: Optional[str] = None,
        update: bool = False,
        version: Optional[str] = None,
        overlay: Optional[str] = None,
        slug: Optional[str] = None,
) -> None:
    """Deploy components to a Kodexa platform instance.
    
    Deploy one or more components (assistants, stores, models, etc.) from JSON/YAML
    files or stdin. Supports batch deployment and metadata overlays for customization.
    
    Arguments:
        FILES: One or more component definition files (JSON/YAML). If omitted, reads from stdin.
    
    Examples:
        # Deploy a single component
        kodexa deploy assistant.json
        
        # Deploy multiple components
        kodexa deploy *.yaml --org my-org
        
        # Update existing component
        kodexa deploy model.json --update
        
        # Deploy with version override
        kodexa deploy assistant.yaml --version 2.0.0
        
        # Deploy from stdin with pipe
        cat component.json | kodexa deploy --format json
        
        # Apply metadata overlay
        kodexa deploy base.json --overlay custom-config.yaml
    """

    if not config_check(url, token):
        return

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
            with open(file, "r", encoding="utf-8") as f:
                if file.lower().endswith(".json"):
                    obj.update(json.load(f))
                elif file.lower().endswith(".yaml") or file.lower().endswith(".yml"):
                    obj.update(yaml.safe_load(f))
                else:
                    raise Exception("Unsupported file type")

                deploy_obj(obj)
    elif files is None:
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
        with open(file, "r", encoding="utf-8") as f:
            if file.lower().endswith(".json"):
                obj = json.load(f)
            elif file.lower().endswith(".yaml") or file.lower().endswith(".yml"):
                obj = yaml.safe_load(f)
            else:
                raise Exception("Unsupported file type")

    print("Deployed :tada:")


@cli.command()
@click.argument("execution_id", required=True)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def logs(_: Info, execution_id: str, url: str, token: str) -> None:
    """Retrieve execution logs for debugging and monitoring.
    
    Fetches the complete log output from a specific execution,
    useful for troubleshooting failed runs or monitoring progress.
    
    Arguments:
        EXECUTION_ID: The ID of the execution to get logs for
    
    Examples:
        # Get logs for an execution
        kodexa logs exec-abc123def456
        
        # Get logs from different environment
        kodexa logs exec-xyz789 --profile production
    """
    if not config_check(url, token):
        return

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
    """Download the implementation package of a model store.
    
    Downloads the complete implementation of a model store including code,
    configurations, and dependencies as a package that can be deployed elsewhere.
    
    Arguments:
        REF: Reference to the model store (e.g., 'org-slug/model-store-slug')
        OUTPUT_FILE: Optional name for the output file (default: 'model_implementation')
    
    Examples:
        # Download with default filename
        kodexa download-implementation my-org/my-model
        
        # Download to specific file
        kodexa download-implementation my-org/my-model my-model-v2.zip
        
        # Download to specific path
        kodexa download-implementation my-org/classifier /backups/classifier-backup
    """

    if not config_check(url, token):
        return
    # We are going to download the implementation of the component
    try:  
        client = KodexaClient(url=url, access_token=token)
        model_store_endpoint: ModelStoreEndpoint = client.get_object_by_ref("store", ref)  
        model_store_endpoint.download_implementation(output_file)  
        print(f"Implementation downloaded successfully to {output_file}")  
    except Exception as e:  
        print_error_message(  
        "Download Failed",  
        f"Could not download implementation for {ref}.",  
        str(e)  
        )  
        sys.exit(1)  

@cli.command()
@click.argument("path", required=True)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def validate_manifest(_: Info, path: str, url: str, token: str) -> None:
    """Validate a Kodexa manifest file.
    
    Checks that a manifest file is correctly formatted and contains valid
    resource definitions before deployment.
    
    Arguments:
        PATH: Path to the manifest file to validate
    
    Examples:
        # Validate a manifest
        kodexa validate-manifest manifest.yaml
        
        # Validate against specific server
        kodexa validate-manifest deployment.json --url https://staging.kodexa.ai
    """
    if not config_check(url, token):
        return

    try:
        client = KodexaClient(url=url, access_token=token)
        client.validate_manifest(path)
        print("Manifest is valid")
    except Exception as e:
        print_error_message(
            "Validation Failed",
            f"Could not validate manifest at {path}.",
            str(e)
        )
        sys.exit(1)


@cli.command("model-costs")
@click.option(
    "--filter", 
    "filters",
    multiple=True,
    help="Filter expression for model costs (e.g., \"createdOn > dateMath('now - 1 day')\")"
)
@click.option(
    "--csv", 
    "output_csv",
    is_flag=True,
    help="Output as CSV format instead of table"
)
@click.option(
    "--output-file",
    help="File path to save the output (CSV or table format)"
)
@click.option(
    "--url", 
    default=get_current_kodexa_url(), 
    help="The URL to the Kodexa server"
)
@click.option(
    "--token", 
    default=get_current_access_token(), 
    help="Access token"
)
@pass_info
def model_costs(
    _: Info,
    filters: tuple[str],
    output_csv: bool,
    output_file: Optional[str],
    url: str,
    token: str
) -> None:
    """Get model costs with optional filtering and export capabilities.
    
    Examples:
        kodexa model-costs
        kodexa model-costs --filter "createdOn > dateMath('now - 1 day')"
        kodexa model-costs --csv --output-file costs.csv
        kodexa model-costs --filter "modelId = 'gpt-4'" --csv
    """
    if not config_check(url, token):
        return

    try:
        client = KodexaClient(url=url, access_token=token)
        
        # Convert filters tuple to list if provided
        filter_list = list(filters) if filters else None
        
        # Get model costs from the API
        model_costs = client.model_costs.get_model_costs(filters=filter_list)
        
        if not model_costs:
            print("No model costs found for the specified filters.")
            return
        
        # Handle CSV output
        if output_csv:
            import io
            output = io.StringIO()
            
            # Define CSV headers based on AggregatedModelCost fields
            headers = [
                "Model ID",
                "Model Name", 
                "Total Tokens",
                "Total Input Tokens",
                "Total Output Tokens",
                "Total Cost",
                "Count"
            ]
            
            writer = csv.writer(output)
            writer.writerow(headers)
            
            # Write data rows
            for cost in model_costs:
                row = [
                    cost.model_id if hasattr(cost, 'model_id') else "",
                    cost.model_name if hasattr(cost, 'model_name') else "",
                    cost.total_tokens if hasattr(cost, 'total_tokens') else 0,
                    cost.total_input_tokens if hasattr(cost, 'total_input_tokens') else 0,
                    cost.total_output_tokens if hasattr(cost, 'total_output_tokens') else 0,
                    f"${cost.total_cost:.4f}" if hasattr(cost, 'total_cost') else "$0.0000",
                    cost.count if hasattr(cost, 'count') else 0
                ]
                writer.writerow(row)
            
            csv_content = output.getvalue()
            
            # Output to file or stdout
            if output_file:
                with open(output_file, 'w', newline='') as f:
                    f.write(csv_content)
                print(f"Model costs exported to {output_file}")
            else:
                # Output to stdout
                print(csv_content, end='')
                global GLOBAL_IGNORE_COMPLETE
                GLOBAL_IGNORE_COMPLETE = True
        
        # Handle table output (default)
        else:
            from rich.table import Table
            from rich.console import Console
            
            table = Table(title="Model Costs", title_style="bold blue")
            table.add_column("Model ID", style="cyan")
            table.add_column("Model Name", style="green")
            table.add_column("Total Tokens", justify="right", style="yellow")
            table.add_column("Input Tokens", justify="right", style="yellow")
            table.add_column("Output Tokens", justify="right", style="yellow")
            table.add_column("Total Cost", justify="right", style="magenta")
            table.add_column("Count", justify="right", style="white")
            
            # Calculate totals
            total_tokens = 0
            total_input = 0
            total_output = 0
            total_cost = 0.0
            total_count = 0
            
            for cost in model_costs:
                tokens = cost.total_tokens if hasattr(cost, 'total_tokens') else 0
                input_tokens = cost.total_input_tokens if hasattr(cost, 'total_input_tokens') else 0
                output_tokens = cost.total_output_tokens if hasattr(cost, 'total_output_tokens') else 0
                cost_value = cost.total_cost if hasattr(cost, 'total_cost') else 0.0
                count = cost.count if hasattr(cost, 'count') else 0
                
                total_tokens += tokens
                total_input += input_tokens
                total_output += output_tokens
                total_cost += cost_value
                total_count += count
                
                table.add_row(
                    cost.model_id if hasattr(cost, 'model_id') else "",
                    cost.model_name if hasattr(cost, 'model_name') else "",
                    f"{tokens:,}",
                    f"{input_tokens:,}",
                    f"{output_tokens:,}",
                    f"${cost_value:.4f}",
                    f"{count:,}"
                )
            
            # Add totals row
            table.add_row(
                "[bold]TOTAL[/bold]",
                "",
                f"[bold]{total_tokens:,}[/bold]",
                f"[bold]{total_input:,}[/bold]",
                f"[bold]{total_output:,}[/bold]",
                f"[bold]${total_cost:.4f}[/bold]",
                f"[bold]{total_count:,}[/bold]",
                style="bold blue"
            )
            
            console = Console()
            
            # Output to file or console
            if output_file:
                with open(output_file, 'w') as f:
                    console_file = Console(file=f, force_terminal=False)
                    console_file.print(table)
                print(f"Model costs table saved to {output_file}")
            else:
                console.print(table)
                
                # Print filter information if provided
                if filters:
                    console.print(f"\nFilters applied: {', '.join(filters)}", style="dim")
    
    except Exception as e:
        print_error_message(
            "Failed to retrieve model costs",
            "Could not fetch model costs from the server.",
            str(e)
        )
        sys.exit(1)


@cli.command()
@click.argument("path", required=True)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def deploy_manifest(_: Info, path: str, url: str, token: str) -> None:
    """Deploy resources defined in a manifest file.
    
    Deploys all components and configurations defined in a Kodexa manifest file.
    Manifests allow you to define entire projects or environments in a single file.
    
    Arguments:
        PATH: Path to the manifest file to deploy
    
    Examples:
        # Deploy a manifest
        kodexa deploy-manifest production-manifest.yaml
        
        # Deploy to specific environment
        kodexa deploy-manifest env/staging.json --profile staging
    """
    if not config_check(url, token):
        return

    try:
        client = KodexaClient(url=url, access_token=token)
        client.deploy_manifest(path)
        print("Manifest deployed successfully")
    except Exception as e:
        print_error_message(
            "Deployment Failed",
            f"Could not deploy manifest from {path}.",
            str(e)
        )
        sys.exit(1)

@cli.command()
@click.argument("project_id", required=True)
@click.option(
    "--url", default=get_current_kodexa_url(), help="The URL to the Kodexa server"
)
@click.option("--token", default=get_current_access_token(), help="Access token")
@pass_info
def get_project_template(_: Info, project_id: str, url: str, token: str) -> None:
    """Get a project template.
    
    Get a project template by ID.
    
    Arguments:
        PROJECT_ID: ID of the project to get the template for
    """
    try:
        client = KodexaClient(url=url, access_token=token)
        project = client.projects.get(project_id)
        project_template = project.create_project_template_request()
         
        # Dump the pydantic model to YAML
        yaml_content = yaml.dump(project_template.model_dump(by_alias=True), indent=4)
        print(yaml_content)
    except Exception as e:
        print_error_message(
            "Failed to get project template",
            "Could not get project template for project ID: " + project_id,
            str(e)
        )
        sys.exit(1)