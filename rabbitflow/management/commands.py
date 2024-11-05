# rabbitflow/management/commands.py

import argparse
import os
import sys

from rabbitflow.scripts.rabbitflow_admin import create_project_structure

def main():
    parser = argparse.ArgumentParser(prog='rabbitflow', description='RabbitFlow Management Utility')
    subparsers = parser.add_subparsers(dest='command', help='Subcommands')

    # Subcomando 'startproject'
    parser_startproject = subparsers.add_parser('startproject', help='Create a new RabbitFlow project')
    parser_startproject.add_argument('name', nargs='?', default='.', help='Name of the project or . for current directory')

    args = parser.parse_args()

    if args.command == 'startproject':
        project_name = args.name
        if project_name == '.':
            project_name = os.path.basename(os.getcwd())
            create_project_structure('.')
        else:
            create_project_structure(project_name)
        print(f"Project '{project_name}' created successfully.")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
