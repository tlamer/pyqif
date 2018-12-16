#!/usr/bin/env python3
"""
Tool for converting csv to qif format.
"""
import os
import re
import sys
import logging
import argparse
import yaml
import datetime
import csv

logging.basicConfig(level=logging.WARN)
LOGGER = logging.getLogger(__name__)

# Default configuration.
DEFAULT_CONFIG = {
    'type': 'Bank',
    'encoding': 'utf-8',
    'date_output': '%Y-%m-%d',
    'delimiter': ','
}


class ExpandPathAction(argparse.Action):
    """
    Action to os.path.userexpand() path.
    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(ExpandPathAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, os.path.expanduser(values))


def parse_account_config(source, account, defaults):
    """
    Parse configuration file and apply defaults.
    """
    cfg = yaml.load(source)

    return {**defaults, **cfg[account]}


def arg_parser():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('account', help="Account name.")
    parser.add_argument(
        '-i',
        '--input',
        action=ExpandPathAction,
        required=True,
        help="Path to csv file. Use stdin if not provided.")
    parser.add_argument(
        '-o',
        '--output',
        action=ExpandPathAction,
        help='Path to output file. Print output to stdout if not specified.')
    parser.add_argument(
        '-c',
        '--config',
        action=ExpandPathAction,
        default=os.path.expanduser('~/.pyqifrc'),
        help="Path to config file. The default is ~/.pyqifrc.")
    parser.add_argument(
        '-d',
        '--debug',
        action='store_const',
        const=logging.DEBUG,
        default=logging.WARN,
        help="Print debug messages.")

    return parser


def gen_header(acc_name, acc_type):
    """
    Generate qif header.
    """
    header = '!Account\nN{n}\nT{t}\n^\n!Type:{t}\n^\n'.format(
        n=acc_name, t=acc_type)
    return header


def process_date(data, in_date, out_date):
    """
    Translate the date accordingly.
    """
    dtm = datetime.datetime.strptime(data, in_date)
    return dtm.date().strftime(out_date)


def process_entry(data, cfg):
    """
    Process csv entry.
    """
    result = ""
    items = cfg['items']

    for item, position in items.items():
        position -= 1

        # Process date.
        if item == "D":
            date = process_date(data[position], cfg['date_input'],
                                cfg['date_output'])
            result += item + date + "\n"

        # Substitute.
        elif item in cfg['substitutions'].keys():
            for pattern, sub in cfg['substitutions'][item].items():
                repl, count = re.subn(
                    pattern, sub, data[position], flags=re.IGNORECASE)
                if count > 0:
                    result += item + repl + '\n'

        # Add value if not empty.
        elif data[position] is not '':
            result += item + data[position] + "\n"

    result += "^\n"

    return result


def process_header(header, cfg):
    """
    Find the position of items from header.
    """
    for key, value in cfg['items'].items():
        if isinstance(value, str):
            try:
                cfg['items'][key] = header.index(value) + 1
            except ValueError as err:
                LOGGER.error(err)
                sys.exit(4)

    LOGGER.debug('Configuration with parsed header %s', cfg)

    return cfg


def main():
    """
    Main function.
    """
    args = arg_parser().parse_args()
    LOGGER.setLevel(args.debug)
    LOGGER.debug(args)

    if not os.path.isfile(args.config):
        LOGGER.warning(
            "File '%s' not found. Provide an existing configuration file.",
            args.config)
        sys.exit(1)

    with open(args.config) as cfg_file:
        account = parse_account_config(cfg_file, args.account, DEFAULT_CONFIG)

    LOGGER.debug('Account configuration: %s', account)

    # Sanity checks.
    if 'items' not in account.keys():
        LOGGER.error('No detail item specified in the configuration.')
        sys.exit(3)

    if 'substitutions' not in account.keys():
        LOGGER.debug('No subtitutions in the config. Add empty item.')
        account['substitutions'] = {}

    if args.output is None:
        output = sys.stdout
    else:
        output = open(args.output, 'wt')

    try:
        output.write(gen_header(args.account, account['type']))
    except KeyError:
        LOGGER.critical('Account type is not specified in configuration.')
        sys.exit(2)

    # Process the data.
    with open(args.input, newline='', encoding=account['encoding']) as csvf:
        source = csv.reader(csvf, delimiter=account['delimiter'])
        account = process_header(source.__next__(), account)

        for data in source:
            output.write(process_entry(data, account))


if __name__ == "__main__":
    main()
