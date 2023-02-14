"""
Utilities to support generating documentation based on the metadata in a kodexa.yml
"""
import os
from pathlib import Path

import jinja2
import yaml
from kodexa import KodexaClient


def camel_to_kebab(s):
    """Convert a camel case string to a kebab case string

    Args:
      s: the string to convert

    Returns:

    """
    return ''.join(['-' + i.lower() if i.isupper() else i for i in s]).lstrip('-')


def get_path():
    """Gets the path of the documentation
    
    :return: the path of this module file

    Args:

    Returns:

    """
    return os.path.abspath(__file__)


def get_template_env():
    """Get the Jinja2 template environmnet
    
    :return:

    Args:

    Returns:

    """
    cli_path = os.path.dirname(get_path())
    package_location = os.path.join(cli_path, "templates")
    template_loader = jinja2.FileSystemLoader([os.getcwd(), package_location])
    return jinja2.Environment(loader=template_loader, autoescape=True)


def generate_documentation(metadata_components):
    """Given the metadata object from a kodexa.yml generate the documentation

    Args:
      metadata:Dict: A dictionary of the metadata

    """
    os.makedirs('docs', exist_ok=True)
    components = document_components(metadata_components)

    try:
        with open("mkdocs.yml", "r") as mkdocs_file:
            mkdocs = yaml.unsafe_load(mkdocs_file.read())
    except FileNotFoundError:
        mkdocs = {'site_name': 'Docs', 'nav': []}

    for reference in mkdocs['nav']:
        if 'Reference' in reference or 'Releases' in reference:
            mkdocs['nav'].remove(reference)

    COMPONENT_NAME_DICT = {
        'actions': 'Actions',
        'dataStores': 'Data Stores',
        'documentStores': 'Document Stores',
        'models': 'Models',
        'projectTemplates': 'Project Templates',
        'pipelines': 'Pipelines',
        'taxonomies': 'Taxonomies',
        'assistantDefinitions': 'Assistant Definitions',
        'modelRuntimes': 'Model Runtimes',
        'extensionPacks': 'Extension Packs'
    }

    new_reference = []
    for component in components:
        if len(components[component]) > 0:
            new_reference.append({COMPONENT_NAME_DICT[component]: []})
            for item in components[component]:
                new_reference[-1][COMPONENT_NAME_DICT[component]].append({item['metadata'].name: item['path']})

    mkdocs['nav'].append({'Reference': new_reference})

    if build_releases():
        mkdocs['nav'].append({'Releases': 'releases/index.md'})

    with open("mkdocs.yml", "w") as mkdocs_file:
        mkdocs_file.write(yaml.dump(mkdocs))


def document_components(metadata_objects):
    components = {
        'actions': [],
        'documentStores': [],
        'dataStores': [],
        'models': [],
        'projectTemplates': [],
        'pipelines': [],
        'taxonomies': [],
        'assistantDefinitions': [],
        'modelRuntimes': [],
        'extensionPacks': []
    }

    client = KodexaClient()

    for metadata in metadata_objects:

        if not isinstance(metadata, dict):
            metadata = metadata.to_dict()
        print("Processing " + metadata['name'])

        component = client.deserialize(metadata)

        if component.type == 'action':
            components['actions'].append(
                write_template("action.jinja2", f"docs/{camel_to_kebab(component.type)}", f"{component.slug}.md",
                               component))

        if component.type == 'store':

            if component.store_type == 'TABLE':
                components['dataStores'].append(
                    write_template("data-store.jinja2", f"docs/{camel_to_kebab(component.type)}",
                                   f"{component.slug}.md",
                                   component))
            elif component.store_type == 'MODEL':
                components['models'].append(
                    write_template("model.jinja2", f"docs/{camel_to_kebab(component.type)}", f"{component.slug}.md",
                                   component))
            else:
                components['documentStores'].append(
                    write_template("document-store.jinja2", f"docs/{camel_to_kebab(component.type)}",
                                   f"{component.slug}.md",
                                   component))

        if component.type == 'projectTemplate':
            components['projectTemplates'].append(
                write_template("project-template.jinja2", f"docs/{camel_to_kebab(component.type)}",
                               f"{component.slug}.md",
                               component))

        if component.type == 'extensionPack':
            components['extensionPacks'].append(
                write_template("extension-pack.jinja2", f"docs/{camel_to_kebab(component.type)}",
                               f"{component.slug}.md",
                               component))

        if component.type == 'pipeline':
            components['pipelines'].append(
                write_template("pipeline.j2", f"docs/{camel_to_kebab(component.type)}", f"{component.slug}.md",
                               component))

        if component.type == 'taxonomy':
            components['taxonomies'].append(
                write_template("taxonomy.jinja2", f"docs/{camel_to_kebab(component.type)}", f"{component.slug}.md",
                               component))

        if component.type == 'assistant':
            components['assistantDefinitions'].append(
                write_template("assistant.jinja2", f"docs/{camel_to_kebab(component.type)}", f"{component.slug}.md",
                               component))

        if component.type == 'modelRuntime':
            components['modelRuntimes'].append(
                write_template("model-runtime.jinja2", f"docs/{camel_to_kebab(component.type)}", f"{component.slug}.md",
                               component))

        if 'services' in metadata:
            service_components = document_components(metadata['services'])
            components['actions'] += service_components['actions']
            components['models'] += service_components['models']
            components['documentStores'] += service_components['documentStores']
            components['dataStores'] += service_components['dataStores']
            components['projectTemplates'] += service_components['projectTemplates']
            components['pipelines'] += service_components['pipelines']
            components['taxonomies'] += service_components['taxonomies']
            components['assistantDefinitions'] += service_components['assistantDefinitions']
            components['modelRuntimes'] += service_components['modelRuntimes']
            components['extensionPacks'] += service_components['extensionPacks']

    return components


def write_template(template, output_location, output_filename, component):
    """
    Write the given template out to a file

    Args:
      template: the name of the template
      output_location: the location to write the output
      output_filename: the name of the output file
      component: the component metadata
    """
    template = get_template_env().get_template(template)
    processed_template = template.render({"component": component})

    from pathlib import Path
    Path(output_location).mkdir(parents=True, exist_ok=True)
    with open(output_location + "/" + output_filename, "w") as text_file:
        text_file.write(processed_template)

    return {'metadata': component,
            'type_name': camel_to_kebab(component.type),
            'path': f"{camel_to_kebab(component.type)}/{component.slug}.md"}


def build_releases():
    """
    Build the releases page
    """
    if Path('releases.yml').is_file():
        import json

        import yaml
        import requests
        import textwrap

        with open('releases.yml') as f:
            releases = yaml.load(f, Loader=yaml.FullLoader)

        markdown = """
        # Releases
        
        The following releases are available:
        
        """

        for release in releases['extensionPacks']:
            release_meta = requests.get(release['url']).json()
            if 'SENTRY_DSN' in release_meta['deployment']['environment']:
                del release_meta['deployment']['environment']['SENTRY_DSN']
            Path(f"docs/releases/").mkdir(parents=True, exist_ok=True)
            release_meta['deployment']['deploymentType'] = 'KUBERNETES'
            Path(f"docs/releases/{release['version']}-kubernetes.json").write_text(
                json.dumps(release_meta))
            release_meta['deployment']['deploymentType'] = 'AWS_LAMBDA'
            Path(f"docs/releases/{release['version']}-lambda.json").write_text(
                json.dumps(release_meta))

            markdown = markdown + f"""## {release_meta['version']}
        
        In order to use this release in a private environment you can download the following files:
            
        * [Kubernetes]({release['version']}-kubernetes.json)
        * [AWS Lambda]({release['version']}-lambda.json)
        
        You can then use the following commands to install.
        
        For Kubernetes:
        
        ```shell
        curl -X POST "https://server-name/api/extensionPacks/kodexa" -H "x-access-token: xxxxxx"  -H "Content-Type: application/json" -d @{release['version']}-kubernetes.json
        ```
        
        For AWS Lambda:
        
        ```shell
        curl -X POST "https://server-name/api/extensionPacks/kodexa" -H "x-access-token: xxxxxx"  -H "Content-Type: application/json" -d @{release['version']}-lambda.json
        ```
        """

            Path(f"docs/releases/index.md").write_text(textwrap.dedent(markdown))
        return True
    else:
        return False
