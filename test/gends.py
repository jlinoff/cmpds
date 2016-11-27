#!/usr/bin/env python
'''
Generate random floating point numbers in a range for testing.

It is used to create datasets to test cmpds.

You can decorate the datasets with a header and record counts to
make them easier to read. That works because cmpds allows you
to specify which column to read in the dataset file.

Typically you would want to generate at least 50 elements to enable
the use of the standard normal distribution (SND) for analysis.
'''
# License: MIT Open Source
# Copyright (c) 2016 by Joe Linoff
import argparse
import datetime
import inspect
import os
import random
import sys


VERSION = '0.1'


def generate_dataset(n, lower, upper):
    '''
    Generate a datasets of n elements in the range [lower..upper].

    A typical call might be something like:
       n = 50
       lower = 98
       upper = 101
    '''
    for i in range(n):
        r = random.uniform(lower, upper)
        yield r


def info(msg, f=1):
    '''
    Write an info message to stdout.
    '''
    lineno = inspect.stack()[f][2]
    print('INFO:{} {}'.format(lineno, msg))


def warn(msg, f=1):
    '''
    Write a warning message to stdout.
    '''
    lineno = inspect.stack()[f][2]
    print('WARNING:{} {}'.format(lineno, msg))


def err(msg, f=1):
    '''
    Write an error message to stderr and exit.
    '''
    lineno = inspect.stack()[f][2]
    sys.stderr.write('ERROR:{} {}\n'.format(lineno, msg))
    sys.exit(1)


def getopts():
    '''
    Get the command line options using argparse.
    '''
    # Trick to capitalize the built-in headers.
    # Unfortunately I can't get rid of the ":" reliably.
    def gettext(s):
        lookup = {
            'usage: ': 'USAGE:',
            'optional arguments': 'OPTIONAL ARGUMENTS',
            'show this help message and exit': 'Show this help message and exit.\n ',
        }
        return lookup.get(s, s)

    argparse._ = gettext  # to capitalize help headers
    base = os.path.basename(sys.argv[0])
    name = os.path.splitext(base)[0]
    usage = '\n  {0} [OPTIONS] <NUM> <LOWER> <UPPER>'.format(base)
    desc = 'DESCRIPTION:{0}'.format('\n  '.join(__doc__.split('\n')))
    epilog = r'''
EXAMPLES:
  # Example 1: help
  $ {0} -h

  # Example 2: generate a dataset that mocks runtimes between
  #            115 and 125 seconds per run.
  #            Typically you would want to generate at least 50
  #            elements to enable the use of the SND for analysis.
  $ {0} 8 115 125
     124.409
     121.153
     116.976
     115.358
     123.128
     121.975
     124.312
     122.044

  # Example 3: generate a dataset that mocks runtimes between
  #            115 and 125 seconds per run and is decorated.
  #            Typically you would want to generate at least 50
  #            elements to enable the use of the SND for analysis.
  $ {0} -D 8 115 125
  # date = 2016-11-24 08:27:49.668509
  # num = 8
  # lower = 115.000
  # upper = 125.000
  # decimal places = 3
      1     116.212
      2     122.327
      3     118.571
      4     120.238
      5     124.852
      6     119.652
      7     116.400
      8     122.446

  # Example 4: generate a dataset that mocks runtimes between
  #            10 and 12 seconds with 2 decimal digits of precision.
  #            Typically you would want to generate at least 50
  #            elements to enable the use of the SND for analysis.
  $ {0} -d 2 6 10 12
  # date = 2016-11-24 08:30:31.039108
  # num = 6
  # lower = 10.000
  # upper = 12.000
  # decimal places = 2
      1       10.30
      2       11.48
      3       10.50
      4       10.25
      5       10.52
      6       11.34
'''.format(base)
    afc = argparse.RawTextHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=afc,
                                     description=desc[:-2],
                                     usage=usage,
                                     epilog=epilog)

    parser.add_argument('-d', '--decimal-places',
                        action='store',
                        type=int,
                        metavar=('NUMBER'),
                        default=3,
                        help='''The number of decimal places.
The default is %(default)s.

''')

    parser.add_argument('-D', '--decorate',
                        action='store_true',
                        help='''Print header and line numbers.

''')

    parser.add_argument('-v', '--verbose',
                        action='count',
                        help='''Increase the level of verbosity.

''')

    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s v{0}'.format(VERSION),
                        help="""Show program's version number and exit.
 """)

    # Positional arguments at the end.
    parser.add_argument('num',
                        nargs=1,
                        action='store',
                        type=int,
                        help='''The number of elements in the dataset.
''')

    parser.add_argument('lower',
                        nargs=1,
                        action='store',
                        type=float,
                        help='''The lower bound.
''')

    parser.add_argument('upper',
                        nargs=1,
                        action='store',
                        type=float,
                        help='''The upper bound.
''')

    opts = parser.parse_args()
    return opts
    

def main():
    '''
    Main entry point.
    '''
    opts = getopts()
    num = opts.num[0]
    lower = opts.lower[0]
    upper = opts.upper[0]

    if lower > upper:
        err('lower bound {} must be less than upper bound {}'.format(lower, upper))

    if opts.decorate:
        print('# date = {}'.format(datetime.datetime.now()))
        print('# num = {}'.format(num))
        print('# lower = {:.3f}'.format(lower))
        print('# upper = {:.3f}'.format(upper))
        print('# decimal places = {}'.format(opts.decimal_places))
    i = 0
    for r in generate_dataset(num, lower, upper):
        if opts.decorate:
            i += 1
            f = '{{:>5}}  {{:>10.{}f}}'.format(opts.decimal_places)
            print(f.format(i, r))
        else:
            f = '{{:>10.{}f}}'.format(opts.decimal_places)
            print(f.format(r))
    
    
if __name__ == '__main__':
    main()
