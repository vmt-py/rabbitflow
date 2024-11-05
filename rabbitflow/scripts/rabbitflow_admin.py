# rabbitflow/scripts/rabbitflow_admin.py

import os
import argparse
import stat

# Plantillas para los archivos generados
TEMPLATE_PROCESSORS = {
    'decode.py': '''\
from rabbitflow import Processor, ProcessResult

class DecodeProcessor(Processor[bytes, bytes]):
    """Processor that decodes messages."""

    def process(self, message: bytes) -> ProcessResult[bytes]:
        # TODO: Implement decoding logic here
        # Example: Decode the message from bytes to a specific format
        return ProcessResult(success=True, data=message)
''',

    'validate.py': '''\
from rabbitflow import Processor, ProcessResult

class ValidateProcessor(Processor[bytes, bytes]):
    """Processor that validates messages."""

    def process(self, message: bytes) -> ProcessResult[bytes]:
        # TODO: Implement validation logic here
        # Example: Validate that the message meets an expected schema or format
        return ProcessResult(success=True, data=message)
''',

    'process.py': '''\
from rabbitflow import Processor, ProcessResult

class ProcessProcessor(Processor[bytes, bytes]):
    """Processor that processes messages."""

    def process(self, message: bytes) -> ProcessResult[bytes]:
        # TODO: Implement processing logic here
        # Example: Process the message and perform actions like saving to a database
        return ProcessResult(success=True, data=message)
'''
}

TEMPLATE_MAIN = '''\
from rabbitflow import RabbitFlow
from processors.decode import DecodeProcessor
from processors.validate import ValidateProcessor
from processors.process import ProcessProcessor
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
        print(f"Unknown mode: {{mode}}")
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

TEMPLATE_INIT = '''\
# Init file for processors package
'''

def create_project_structure(project_name):
    base_dir = os.path.abspath(project_name)
    os.makedirs(base_dir, exist_ok=True)

    # Crear el archivo __init__.py en el directorio principal
    init_main_path = os.path.join(base_dir, '__init__.py')
    with open(init_main_path, 'w') as f:
        f.write('''\
# Init file for the main project package
''')

    # Crear la carpeta 'processors' y su __init__.py
    processors_dir = os.path.join(base_dir, 'processors')
    os.makedirs(processors_dir, exist_ok=True)

    init_processors_path = os.path.join(processors_dir, '__init__.py')
    with open(init_processors_path, 'w') as f:
        f.write(TEMPLATE_INIT)

    # Crear los archivos de procesadores dentro de 'processors'
    for filename, content in TEMPLATE_PROCESSORS.items():
        file_path = os.path.join(processors_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)

    # Crear main.py
    main_py = TEMPLATE_MAIN.format(project_name=project_name)
    main_py_path = os.path.join(base_dir, 'main.py')
    with open(main_py_path, 'w') as f:
        f.write(main_py)

    # Crear settings.py
    settings_py = TEMPLATE_SETTINGS.format(project_name=project_name)
    settings_py_path = os.path.join(base_dir, 'settings.py')
    with open(settings_py_path, 'w') as f:
        f.write(settings_py)

    # Crear conexion.py
    conexion_py_path = os.path.join(base_dir, 'conexion.py')
    with open(conexion_py_path, 'w') as f:
        f.write(TEMPLATE_CONEXION)

    # Crear __init__.py en el directorio 'rabbitflow'
    # Esto es necesario si 'rabbitflow' es el paquete raíz
    # Dependiendo de tu estructura, ajusta esto si es necesario
    # init_root_path = os.path.join(base_dir, 'rabbitflow', '__init__.py')
    # os.makedirs(os.path.dirname(init_root_path), exist_ok=True)
    # with open(init_root_path, 'w') as f:
    #     f.write('''\
    # # Init file for rabbitflow package
    # ''')

    print(f"Project '{project_name}' created successfully at {base_dir}.")

def main():
    parser = argparse.ArgumentParser(description='RabbitFlow Project Generator')
    parser.add_argument('project_name', help='Name of the RabbitFlow project')

    args = parser.parse_args()
    create_project_structure(args.project_name)

if __name__ == "__main__":
    main()
