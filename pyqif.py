#!/usr/bin/env python3
"""
Tool for converting csv to qif format.
"""
import os
import sys
import logging
import argparse
import configparser
import datetime
import csv

logging.basicConfig(level=logging.WARN)
LOGGER = logging.getLogger(__name__)

# Default configuration.
DEFAULT_CONFIG = {
    'type': 'Bank',
    'encoding': 'utf-8',
    'separator': ',',
    'tail': '1',  # Discard first X number of lines from the input.
    'decimal': '.',
    'in_date': '%d/%m/%Y',
    'out_date': '%Y-%m-%d'
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
    items = {
        item.upper(): cfg.getint(item) - 1
        for item in cfg.keys() if len(item) <= 2
    }

    for item, position in items.items():
        if item == "D":
            date = process_date(data[position], cfg['in_date'],
                                cfg['out_date'])
            result += item + date + "\n"
        else:
            result += item + data[position] + "\n"

    result += "^\n"

    return result


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

    cfg = configparser.RawConfigParser()

    # Apply configuration defaults and read the config.
    for option, item in DEFAULT_CONFIG.items():
        cfg['DEFAULT'][option] = item
    cfg.read(args.config)

    account = cfg[args.account]

    # Check if there are necessary sections in the config file.
    if args.account not in cfg.sections():
        LOGGER.warning("'%s' section is missing in configuration file.",
                       args.account)
        sys.exit(2)

    if args.output is None:
        output = sys.stdout
    else:
        output = open(args.output, 'wt')

    output.write(gen_header(args.account, account['type']))

    # Process the data.
    with open(args.input, newline='', encoding=account['encoding']) as csvf:
        for indice, data in enumerate(csv.reader(csvf)):
            if indice < account.getint('tail'):
                continue
            output.write(process_entry(data, account))


if __name__ == "__main__":
    main()
