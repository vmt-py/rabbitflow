import os
import argparse

TEMPLATE_PROCESSORS = [
    ('decode.py', '''\
from rabbitflow import Processor, ProcessResult

class DecodeProcessor(Processor[bytes, bytes]):
    """Processor that decodes messages."""

    def process(self, message: bytes) -> ProcessResult[bytes]:
        # TODO: Implement decoding logic here
        # Example: Decode the message from bytes to a specific format
        return ProcessResult(success=True, data=message)
'''),
    ('validate.py', '''\
from rabbitflow import Processor, ProcessResult

class ValidateProcessor(Processor[bytes, bytes]):
    """Processor that validates messages."""

    def process(self, message: bytes) -> ProcessResult[bytes]:
        # TODO: Implement validation logic here
        # Example: Validate that the message meets an expected schema or format
        return ProcessResult(success=True, data=message)
'''),
    ('process.py', '''\
from rabbitflow import Processor, ProcessResult

class ProcessProcessor(Processor[bytes, bytes]):
    """Processor that processes messages."""

    def process(self, message: bytes) -> ProcessResult[bytes]:
        # TODO: Implement processing logic here
        # Example: Process the message and perform actions like saving to a database
        return ProcessResult(success=True, data=message)
''')
]

TEMPLATE_MAIN = '''\
from rabbitflow import RabbitFlow
from decode import DecodeProcessor
from validate import ValidateProcessor
from process import ProcessProcessor
from conexion import rabbit_params

def create_app(mode='all', app_name='{project_name}'):
    # Create an instance of RabbitFlow with the application name and connection parameters
    app = RabbitFlow(name=app_name, rabbit_params=rabbit_params)

    # Register processors based on the mode
    if mode == 'decoder':
        app.register_processor(stage="raw", processor_cls=DecodeProcessor, output_stage="decoded")
    elif mode == 'validator':
        app.register_processor(stage="decoded.success", processor_cls=ValidateProcessor, output_stage="validated")
    elif mode == 'processor':
        app.register_processor(stage="validated.success", processor_cls=ProcessProcessor, output_stage="processed")
    elif mode == 'all':
        # Register all processors in order
        app.register_processor(stage="raw", processor_cls=DecodeProcessor, output_stage="decoded")
        app.register_processor(stage="decoded.success", processor_cls=ValidateProcessor, output_stage="validated")
        app.register_processor(stage="validated.success", processor_cls=ProcessProcessor, output_stage="processed")
    else:
        print(f"Unknown mode: {mode}")
        exit(1)

    return app

def main():
    app = create_app()
    # Start the application to begin processing messages
    app.run()

if __name__ == "__main__":
    main()
'''

TEMPLATE_SETTINGS = '''\
# Application configuration

# Name of the RabbitFlow application
APP_NAME = '{project_name}'

# Additional settings can be added here
'''

TEMPLATE_CONEXION = '''\
import pika

# Connection configuration without SSL (uncommented by default)
rabbit_params = pika.ConnectionParameters(
    host='localhost',
    port=5672,
    credentials=pika.PlainCredentials('guest', 'guest')
)

# Connection configuration with SSL (commented by default)
# Uncomment and configure the parameters according to your needs
# import ssl
# ssl_context = ssl.create_default_context()
# rabbit_params = pika.ConnectionParameters(
#     host='your_rabbitmq_host',
#     port=5671,
#     ssl_options=pika.SSLOptions(context=ssl_context)
# )
'''

TEMPLATE_MANAGE = '''\
#!/usr/bin/env python
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='RabbitFlow Management Utility')
    subparsers = parser.add_subparsers(dest='command', help='Subcommands')

    # Subcommand 'startrabbit'
    parser_startrabbit = subparsers.add_parser('startrabbit', help='Start RabbitMQ server')
    parser_startrabbit.add_argument('action', choices=['start', 'stop', 'restart'], help='Action to perform')

    # Subcommand 'runapp'
    parser_runapp = subparsers.add_parser('runapp', help='Run RabbitFlow application')
    parser_runapp.add_argument('--mode', choices=['decoder', 'validator', 'processor', 'all'], default='all', help='Mode to run the application')

    args = parser.parse_args()

    if args.command == 'startrabbit':
        from rabbitmq_server import (
            start_rabbitmq_server,
            stop_rabbitmq_server,
            restart_rabbitmq_server,
        )
        action = args.action
        if action == 'start':
            start_rabbitmq_server()
        elif action == 'stop':
            stop_rabbitmq_server()
        elif action == 'restart':
            restart_rabbitmq_server()

    elif args.command == 'runapp':
        mode = args.mode
        # Load settings from settings.py
        try:
            import settings
        except ImportError:
            print("Error: Cannot find 'settings.py' in the current directory.")
            sys.exit(1)
        # Run the application
        run_application(mode, settings.APP_NAME)

    else:
        parser.print_help()

def run_application(mode, app_name):
    # Import the user's application
    try:
        from main import create_app
    except ImportError:
        print("Error: Cannot find 'main.py' with 'create_app' function in the current directory.")
        sys.exit(1)

    app = create_app(mode, app_name)
    app.run()

if __name__ == '__main__':
    main()
'''

TEMPLATE_RABBITMQ_SERVER = '''\
import docker
from docker.models.containers import Container

def start_rabbitmq_server():
    client = docker.from_env()

    container_name = 'rabbitmq_server'

    # Check if the container is already running
    try:
        container = client.containers.get(container_name)
        print(f"The container '{container_name}' is already running.")
        return
    except docker.errors.NotFound:
        pass

    env_vars = {
        'RABBITMQ_DEFAULT_USER': 'guest',
        'RABBITMQ_DEFAULT_PASS': 'guest',
        'RABBITMQ_DEFAULT_VHOST': '/',
        'RABBITMQ_LOOPBACK_USERS': 'none'
    }

    ports = {
        '5672/tcp': 5672,
        '15672/tcp': 15672
    }

    print("Starting RabbitMQ container...")
    container = client.containers.run(
        'rabbitmq:3-management',
        name=container_name,
        environment=env_vars,
        ports=ports,
        detach=True
    )

    print(f"Container '{container_name}' started successfully.")

def stop_rabbitmq_server():
    client = docker.from_env()
    container_name = 'rabbitmq_server'

    try:
        container = client.containers.get(container_name)
        container.stop()
        container.remove()
        print(f"Container '{container_name}' stopped and removed.")
    except docker.errors.NotFound:
        print(f"No container named '{container_name}' found.")

def restart_rabbitmq_server():
    stop_rabbitmq_server()
    start_rabbitmq_server()
'''

def create_project_structure(project_name):
    base_dir = os.path.abspath(project_name)
    os.makedirs(base_dir, exist_ok=True)

    # Create processor files in the main directory
    for filename, content in TEMPLATE_PROCESSORS:
        file_path = os.path.join(base_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)

    # Create main.py
    main_py = TEMPLATE_MAIN.format(project_name=project_name)
    with open(os.path.join(base_dir, 'main.py'), 'w') as f:
        f.write(main_py)

    # Create settings.py
    settings_py = TEMPLATE_SETTINGS.format(project_name=project_name)
    with open(os.path.join(base_dir, 'settings.py'), 'w') as f:
        f.write(settings_py)

    # Create conexion.py
    with open(os.path.join(base_dir, 'conexion.py'), 'w') as f:
        f.write(TEMPLATE_CONEXION)

    # Create manage.py
    with open(os.path.join(base_dir, 'manage.py'), 'w') as f:
        f.write(TEMPLATE_MANAGE)

    # Make manage.py executable
    os.chmod(os.path.join(base_dir, 'manage.py'), 0o755)

    # Create rabbitmq_server.py
    with open(os.path.join(base_dir, 'rabbitmq_server.py'), 'w') as f:
        f.write(TEMPLATE_RABBITMQ_SERVER)

    print(f"Project '{project_name}' created successfully at {base_dir}.")

def main():
    parser = argparse.ArgumentParser(description='RabbitFlow Project Generator')
    parser.add_argument('project_name', help='Name of the RabbitFlow project')

    args = parser.parse_args()
    create_project_structure(args.project_name)

if __name__ == "__main__":
    main()
