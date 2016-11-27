#!/usr/bin/env python
r'''
Compare two datasets to determine whether there is a significant
difference between them for a specific confidence level using the
t-test methodology for unpaired observations.

Please note that this is not, strictly, a t-test because it switches
over to the standard normal distribution (SND) when the number of
effective degrees of freedom (DOF) is larger than 32.

It is really useful for determining whether runtime or memory use has
changed between two different versions of software. The datasets are
completely independent of the program (i.e. the data values are
created by tools like /usr/bin/time) so they can be used in a black
box testing environment.

Each dataset contains a series of numbers to be compared. The numbers
must be greater than 0. That is a reasonable constraint given that
they typically represent something like elapsed time or memory used.

The size of the datasets can be different because we are treating
the samples as unpaired observations (t-test) but the smallest one
must have more than 2 entries. Typically you would like to have
at least 50 entries in each dataset.

You must specify the confidence level that you want to use to
determine whether the datasets differ. Typical confidence levels 0.90
(90%), 0.95 (95%) and 0.99 (99%). The tool will automatically
determine the associated z-value based on the confidence level and the
number of effective degrees of freedom. No table look ups are
necessary. The methodology used to calculate the z-value is described
in detail here: https://github.com/jlinoff/ztables.

To determine significance, you specify the confidence level that you
want to use to determine significance. Typical confidence levels 0.90
(90%), 0.95 (95%) and 0.99 (99%). The tool will automatically
determine the associated z-value based on the confidence level and the
number of effective degrees of freedom. No table look ups are
necessary.


EXAMPLE 1 - two datasets in one file

Here is an example to make sense of it all.

We want to compare two versions of the foobar program to see if the
second version is faster than the first for the same inputs. The
versions are 1.1 and 1.2. The program takes about 2 minutes to run
(120 seconds) and we want to determine whether v1.2 is faster.
The table below shows sample data 10 runs for each version.

   # Run time data collected for v1.1 and v1.2.
   #
   # Num   v1.1      v1.2
   # ===   =======   =======
       1   119.041   117.038
       2   119.670   119.733
       3   120.675   118.346
       4   118.628   117.261
       5   120.363   118.863
       6   118.076   117.545
       7   120.539   119.751
       8   118.880   119.042
       9   120.164   116.203
      10   119.134   118.049

For this example we assume that the data is stored in a single file
but normally it is easier to have it exist in two separate files
because, by default, the tool looks at the first token on each line
and collects it if the token is a floating point number. When the data
is not in a single column in a file, you must explicitly specify the
which column to collect. In this case, the first dataset is in column
2 and the second dataset is in column 3 of the same file. Blank lines
and lines where the token is not a floating point number are ignored.

Here is what the run looks like:

   $ ./cmpds.py -c 0.95 -k 2 3 data.txt
   With 95.0% confidence, dataset-2 is smaller than dataset-1 by about 1.1%.

As you can see, dataset-2 (v1.2) is slightly faster.

Note that we use -k to specify the columns because -c is already
reserved for specifying the confidence level.

If you reverse the columns, you will get the opposite result:

   $ ./cmpds.py -c 0.95 -k 3 2 data.txt
   With 95.0% confidence, dataset-2 is larger than dataset-1 by about 1.1%.


EXAMPLE 2 - datasets in separate files

A more realistic example would be running a program called blackbox-v1
50 times and collecting the timing output to a file and then running
blackbox-v2 and collecting its output. Here is how you might do it:

   $ rm -f /tmp/blackbox-v1.out /tmp/blackbox-v2.out
   $ for((i=1;i<=50;i++)) ; do printf '\nExp %03d\n' $i ; /usr/bin/time -p blackbox-v1 >> /tmp/v1.out ; done
   $ for((i=1;i<=50;i++)) ; do printf '\nExp %03d\n' $i ; /usr/bin/time -p blackbox-v2 >> /tmp/v2.out ; done

We can now capture the real run time data by simply grepping out the
data like this:

   $ grep -w ^real /tmp/v1.out > /tmp/v1.ds
   $ grep -w ^real /tmp/v2.out > /tmp/v2.ds

The above command takes advantage of the fact that posix time format
(-p) outputs the time data on 3 separate lines as shown in this simple
example:

   $ /usr/bin/time -p sleep 0.3
   real         0.30
   user         0.00
   sys          0.00

At this point we have the unpaired observations from both runs in two
different files so we can use cmpds.py to figure out whether v2 is
faster than v1 at a 95% confidence level.

   $ ./cmpds.py -c 0.95 /tmp/v1.ds /tmp/v2.ds
   With 95.0% confidence, dataset-2 is smaller than dataset-1 by about 1.3%.

That tells us that v2 is indeed slightly faster.
'''
# License: MIT Open Source
# Copyright (c) 2016 by Joe Linoff
#REFERENCES:
#    Jain, Raj (1991). "The Art Computer Systems Performance Analysis", John Wiley and Sons, New York.
import argparse
import datetime
import inspect
import math
import os
import sys


VERSION='0.1'

# ================================================================
#
# Message utility functions.
#
# ================================================================
def _msg(prefix, frame, msg, ofp=sys.stdout):
    '''
    Base for printing messages.
    '''
    lineno = inspect.stack()[frame][2]
    now = datetime.datetime.now()
    ofp.write('{!s:<26} {} {:>5} - {}\n'.format(now, prefix, lineno, msg))


def info(msg, f=1):
    '''
    Write an info message to stdout.
    '''
    _msg('INFO', f+1, msg)


def infov(opts, msg, f=1):
    '''
    Write an info message to stdout.
    '''
    if opts.verbose > 0:
        _msg('INFO', f+1, msg)


def warn(msg, f=1):
    '''
    Write a warning message to stdout.
    '''
    _msg('WARNING', f+1, msg)


def err(msg, f=1):
    '''
    Write an error message to stderr and exit.
    '''
    _msg('ERROR', f+1, msg, sys.stderr)
    sys.exit(1)


# ================================================================
#
# Statistical utility functions.
# See https://github.com/jlinoff/ztables for background.
#
# ================================================================
def gamma(x):
    '''
    Gamma function.

    Uses the Lanczos approximation and natural logarithms.

    For integer values of x we can use the exact value of (x-1)!.

       gamma(1/2) = 1.77245385091
       gamma(3/2) = 0.886226925453
       gamma(5/2) = 1.32934038818
       gamma(7/2) = 3.32335097045
       gamma(4)   = 6.0
    '''
    if (x - int(x)) == 0:
        # Optimization for integer values: (x-1)!.
        return reduce(lambda a, b: a * b, [float(i) for i in range(1, int(x))])

    # Lanczos approximation, page 214 of Numerical Recipes in C.
    c = [76.18009172947146,
         -86.50532032941677,
         24.01409824083091,
         -1.231739572450155,
         0.1208650973866179e-2,
         -0.5395239384953e-5,
    ]
    c0 = 1.000000000190015
    c1 = 2.5066282746310005
    x1 = float(x) + 5.5
    x2 = (float(x) + 0.5) * math.log(x1)
    x3 = x1 - x2
    x4 = c0
    x5 = float(x)
    for i in range(6):
        x5 += 1.0
        x4 += c[i] / x5
    x6 = math.log((c1 * x4) / float(x))
    x7 = -x3 + x6  # ln(gamma(x))
    g = math.exp(x7)
    return g


def pdf_t(x, dof):
    '''
    Calculate the probability density function (PDF) at x for a
    student-t distribution with dof degrees of freedom.

    This is basically the height of the curve at x.
    '''
    assert dof > 2

    x1 = gamma((float(dof) + 1.0) / 2.0)
    x2 = math.sqrt(dof * math.pi) * gamma((float(dof) / 2.0))
    x3 = 1.0 + (float((x ** 2)) / float(dof))
    x4 = float((dof + 1)) / 2.0
    x5 = x3 ** -x4

    y = (x1 * x5) / x2
    return y


def pdf_nd(x, s=1.0, u=0.0):
    '''
    Calculate the probability density function (PDF) for a normal
    distribution.

    s = standard deviation (1 for a standard normal distribution)
    u = mean (0 for a standard normal distribution)

    This is the height of the curve at x.
    '''
    dx = float(x) - float(u)
    dx2 = dx * dx
    xden = 2 * (s ** 2)
    den = s * math.sqrt(2 * math.pi)
    exp = math.e ** ( -dx2 / xden )
    y =  exp / den
    return y


def pdf_snd(x):
    '''
    Calculate the probability density function (PDF) for a standard
    normal distribution.

    s = standard deviation (1 for a standard normal distribution)
    u = mean (0 for a standard normal distribution)

    This is the height of the curve at x.

    It is exactly the same as pdf_nd(x, 1, 0) but is somewhat more
    efficient.
    '''
    dx2 = float(x) ** 2
    den = math.sqrt(2 * math.pi)
    exp = math.e ** - (dx2 / 2)
    y =  exp / den
    return y


def area_under_curve(x1, x2, intervals, fct, *args, **kwargs):
    '''
    Calculate the approximate area under a curve using trapezoidal
    approximation.

    It breaks the interval between x1 and x2 into trapezoids whose
    width is fixed (proportional to how the interval is sliced). The
    height of each rectangle is the pdf function value for x at the
    start of the interval. The accumulation of the areas provides an
    estimate of the area under the curve.

    The greater the number of intervals the better the estimate is at
    the cost of performance.
    '''
    assert x2 > x1  # just a sanity check
    assert intervals > 1  # another sanity check

    total_area = 0.0
    width = (float(x2) - float(x1)) / float(intervals)

    x = float(x1)
    py = float(fct(x, *args, **kwargs))
    for i in range(intervals):
        y = float(fct(x, *args, **kwargs))
        rectangle_area = width * y  # area of rectangle at x with height y
        triangle_area = ((y - py) * width) / 2.0  # adjustment based on height change
        total_area += rectangle_area + triangle_area  # trapezoid area
        x += width  # advance to the next edge
        py = y  # remember the previous height

    return total_area


def binary_search_for_z(probability, tolerance, maxtop, minval, iterations, v, fct, *args):
    '''
    Get the z value that matches the specified percentage.
    '''
    # Binary search to find the closest value.
    z = 0.0
    adjustment = float(maxtop) / 2.0
    top = maxtop
    bot = 0.0
    diff = tolerance * 2  # start the loop
    while diff > tolerance:
        mid = bot + ((top - bot) / 2.0)
        z = mid - adjustment
        q = area_under_curve(minval, z, iterations, fct, *args)
        cp = 1.0 - (2.0 * (1.0 - q))
        diff = abs(cp - probability)
        if v:
            info('p={}, cp={}, t={:f}, mt={}, mv={}, i={}, top={}, bot={}, mid={}, z={}, q={}'.format(
                probability, cp, tolerance, maxtop, minval, iterations, top, bot, mid, z, q))

        if probability < cp:
            # It is to the right.
            top = mid
        elif probability > cp:
            # It is to the left.
            bot = mid
        else:
            break

        # Sanity checks.
        assert top <= maxtop
        assert bot >= 0

    return z


# ================================================================
#
# t-test implementation
#
# ================================================================
def ttest(a, b, opts):
    '''
    Analyze unpaired observations to determine whether they are
    significantly different.
    '''
    cl = opts.conf
    infov(opts, 'a: {:>3} {}'.format(len(a), a))
    infov(opts, 'b: {:>3} {}'.format(len(b), b))
    infov(opts, 'confidence level: {:.1f}%'.format(100.*cl))

    na = float(len(a))
    nb = float(len(b))
    infov(opts, 'na: {}'.format(na))
    infov(opts, 'nb: {}'.format(nb))

    # means
    ma = sum(a) / na
    mb = sum(b) / nb
    infov(opts, 'mean a: {:.3f}'.format(ma))
    infov(opts, 'mean b: {:.3f}'.format(mb))

    # standard deviations
    stddev_suma2 = sum([x**2 for x in a])
    stddev_sumb2 = sum([x**2 for x in b])
    infov(opts, 'stddev sum a^2: {:.3f}'.format(stddev_suma2))
    infov(opts, 'stddev sum b^2: {:.3f}'.format(stddev_sumb2))

    stddev_nma2 = na * ma ** 2
    stddev_nmb2 = nb * mb ** 2
    infov(opts, 'stddev na * ma^2: {:.3f}'.format(stddev_nma2))
    infov(opts, 'stddev nb * mb^2: {:.3f}'.format(stddev_nmb2))

    vara = (stddev_suma2 - stddev_nma2) / float(na - 1.)
    varb = (stddev_sumb2 - stddev_nmb2) / float(nb - 1.)
    infov(opts, 'variance a: {:.3f}'.format(vara))
    infov(opts, 'variance b: {:.3f}'.format(varb))

    stddeva = math.sqrt(vara)
    stddevb = math.sqrt(varb)
    infov(opts, 'stddev a: {:.3f}'.format(stddeva))
    infov(opts, 'stddev b: {:.3f}'.format(stddevb))

    # mean difference
    md = ma - mb
    infov(opts, 'mean diff: {:.3f}'.format(md))

    # standard deviation of the mean difference
    sa2qna = stddeva**2 / na
    sb2qnb = stddevb**2 / nb
    sdmd = math.sqrt(sa2qna + sb2qnb)
    infov(opts, 'stddev of the mean diff: {:.3f}'.format(sdmd))

    # effective degrees of freedom
    dof_num = (sa2qna + sb2qnb)**2
    dof_dena = (1. / (na + 1.)) * sa2qna**2
    dof_denb = (1. / (nb + 1.)) * sb2qnb**2
    dof = (dof_num / (dof_dena + dof_denb)) - 2.0
    infov(opts, 'effective DOF: {:.2f}'.format(dof))
    dofr = int('{:.0f}'.format(dof))
    infov(opts, 'effective DOF (rounded): {}'.format(dofr))

    # confidence interval for the mean difference
    z = 0.0

    # allow the user to play with the parameters
    t = opts.internal[0]
    lb = opts.internal[1]
    ub = opts.internal[2]
    intervals = int(opts.internal[3])

    maxv = 2 * round(abs(lb) + ub + 0.5, 0)
    minv = -maxv
    infov(opts, 'internal threshold: {:.1f}'.format(t))
    infov(opts, 'internal lower bound: {}'.format(lb))
    infov(opts, 'internal upper bound: {}'.format(ub))
    infov(opts, 'internal intervals: {}'.format(intervals))
    infov(opts, 'internal minval: {}'.format(minv))
    infov(opts, 'internal maxval: {}'.format(maxv))
    v = True if opts.verbose > 1 else False
    if dofr > opts.snd_threshold:
        # use standard normal distribution (SND)
        infov(opts, 'use standard normal distribution (SND)')
        z = binary_search_for_z(cl, t, maxv, minv, intervals, v, pdf_snd)
    else:
        infov(opts, 'use t-{} distribution'.format(dofr))
        z = binary_search_for_z(cl, t, maxv, minv, intervals, v, pdf_t, dof)
    x = (1. - cl) / 2.
    q = cl + x
    infov(opts, '{:.3f}-quantile of t-variate with {} degrees of freedom: {:.2f}'.format(q, dofr, z))
    cllb = md - z * sdmd
    club = md + z * sdmd
    infov(opts, '{:.1f}% confidence interval for difference: [{:3f} .. {:3f}]'.format(100.*cl, cllb, club))
    crosses_zero = cllb < 0 < club
    significant = not crosses_zero
    infov(opts, 'crosses zero: {}'.format(crosses_zero))
    infov(opts, 'reject the null hypothesis: {}'.format(significant))

    # Report the result.
    clp = cl * 100.
    if significant:
        per = 100. * abs(md) / ma
        infov(opts, 'precentage: {}'.format(per))
        if club < 0:
            print('With {:.1f}% confidence, dataset-2 is larger than dataset-1 by about {:,.1f}%.'.format(clp, per))
        else:
            print('With {:.1f}% confidence, dataset-2 is smaller than dataset-1 by about {:,.1f}%.'.format(clp, per))
    else:
        print('With {:.1f}% confidence, there is no significant difference between the datasets.'.format(clp))


# ================================================================
#
# Options
#
# ================================================================
def getopts():
    '''
    Get the command line options using argparse.
    '''
    # Make sure that the confidence level is in the proper range.
    def get_conf_level():
        class GetConfLevel(argparse.Action):
            def __call__(self, parser, args, values, option_string=None):
                if 0. < values < 1.0:
                    setattr(args, self.dest, values)
                else:
                    msg = 'argument "{}" out of range (0..1)'.format(self.dest)
                    parser.error(msg)
        return GetConfLevel
    
    # Trick to capitalize the built-in headers.
    # Unfortunately I can't get rid of the ":" reliably.
    def gettext(s):
        lookup = {
            'usage: ': 'USAGE:',
            'positional arguments': 'POSITIONAL ARGUMENTS',
            'optional arguments': 'OPTIONAL ARGUMENTS',
            'show this help message and exit': 'Show this help message and exit.\n ',
        }
        return lookup.get(s, s)

    argparse._ = gettext  # to capitalize help headers
    base = os.path.basename(sys.argv[0])
    name = os.path.splitext(base)[0]
    usage = '\n  {0} [OPTIONS] <DATASET-1> [<DATASET-2>]'.format(base)
    desc = 'DESCRIPTION:{0}'.format('\n  '.join(__doc__.split('\n')))
    epilog = r'''
EXAMPLES:
   # Example 1: help
   $ {0} -h

   # Example 2: No significant difference with 95% confidence.
   #            The dataset is used.
   $ ./gends.py 10 100 120 > ds-10-100-120.txt
   $ {0} ds-10-100-120.txt ds-10-100-120.txt
   With 95.0% confidence, there is no significant difference between the datasets.

   # Example 3: Dataset-2 is slightly smaller (has faster runtime) with 95% confidence.
   #            Both runs have 50 samples.
   #            The data is specifically generated to show the difference.
   $ ./gends.py 50 110 112 > ds-50-110-112.txt
   $ ./gends.py 50 108 112 > ds-50-108-112.txt
   $ {0} ds-50-110-112.txt ds-50-108-112.txt
   With 95.0% confidence, dataset-2 is smaller than dataset-1 by about 0.8%.

   # Example 4: Dataset-2 is slightly smaller (has faster runtime) with 99% confidence.
   #            Both runs have 50 samples.
   $ {0} ds-50-110-112.txt ds-50-108-112.txt
   With 99.0% confidence, dataset-2 is smaller than dataset-1 by about 0.8%.

   # Example 5: Dataset-1 and dataset-2 are in the same file.
   $ cat data.txt
    #   v1.1      v1.2
    #   =======   =======
    1   119.041   117.038
    2   119.670   119.733
    3   120.675   118.346
    4   118.628   117.261
    5   120.363   118.863
    6   118.076   117.545
    7   120.539   119.751
    8   118.880   119.042
    9   120.164   116.203
   10   119.134   118.049
   $ {0} --cols 2 3 data.txt
   With 95.0% confidence, dataset-2 is smaller than dataset-1 by about 1.1%.
 '''.format(base)
    afc = argparse.RawTextHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=afc,
                                     description=desc[:-2],
                                     usage=usage,
                                     epilog=epilog)

    parser.add_argument('-c', '--conf',
                        type=float,
                        default=0.95,
                        action=get_conf_level(),
                        metavar=('FLOAT'),
                        help='''The confidence level such that 0 < c < 1.
The default is %(default)s.
 ''')

    parser.add_argument('--internal',
                        type=float,
                        nargs=4,
                        default=[0.00001, -3.4, 3.4, 10000],
                        metavar=('TOLERANCE', 'LOWER', 'UPPER', 'INTERVALS'),
                        help='''Factors used for internal computations.
You should never need to change these.
Defaults: %(default)s.
 ''')
    
    parser.add_argument('-k', '--cols',
                        nargs=2,
                        type=int,
                        default=[1,1],
                        metavar=('COL1', 'COL2'),
                        help='''The columns that define each dataset.
The first column is for the first dataset.
The second column is for the second dataset.
If the value in the column is not a floating point
number it is ignored.
The default is column 1 for both datasets.
 ''')

    parser.add_argument('-s', '--snd-threshold',
                        type=int,
                        default=32,
                        metavar=('UINT'),
                        help='''The standard normal distribution (SND) threshold.
When the number of effective degrees of freedom (DOF)
exceeds this threshold, the SND is used instead of a
t-distribution.
The default is %(default)s.
 ''')
    
    parser.add_argument('-v', '--verbose',
                        action='count',
                        help='''Increase the level of verbosity.
Specify -v to see the values that make up the computation.
Specify -v -v to internal details about the z value lookup and
values that were discarded during file reads.
 ''')

    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s v{0}'.format(VERSION),
                        help="""Show program's version number and exit.
 """)

    # Positional arguments at the end.
    parser.add_argument('FILES',
                        nargs='+',
                        help='''The files with the run time data.
The data must be organized in columns with one entry per line.
Non-numeric data is ignored which allows you to add comments
and blank spaces.
You can see the ignored data in verbose mode.
If only one file is specified, is used for both datasets.
''')

    opts = parser.parse_args()
    if opts.cols[0] < 1:
        parser.error('column 1 must be greater then 0')
    if opts.cols[1] < 1:
        parser.error('column 1 must be greater then 0')
    if len(opts.FILES) > 2:
        parser.error('only 1 or 2 files may be specified')
    if opts.snd_threshold < 30:
        parser.error('it does not make sense to use SND for {} elements'.format(opts.snd_threshold))
    return opts


# ================================================================
#
# Read file data.
#
# ================================================================
def read_file(opts, fn, col):
    '''
    Read column data from the file.
    '''
    ds = []
    try:
        with open(fn, 'r') as ifp:
            ln = 0
            for line in ifp.readlines():
                ln += 1
                line = line.strip()
                tokens = line.split()
                if len(tokens) < col:
                    continue
                token = tokens[col-1]
                try:
                    f = float(token)
                    if f < 0.0001:  # avoid divide by 0 errors
                        if opts.verbose > 1:
                            info('skipping line {} in {}: number is too small {}'.format(ln, fn, token))
                        continue
                    ds.append(f)
                except ValueError:
                    if opts.verbose > 1:
                        info('skipping line {} in {}: not a number: {}'.format(ln, fn, token))
                    continue
    except IOError:
        err('could not read file: {}'.format(fn))
    if len(ds) < 3:
        err('too few data points at column {}, found {}, need at least 3 in file: {}'.format(col, len(ds), fn))
    return ds
                    

# ================================================================
#
# Main
#
# ================================================================
def main():
    opts = getopts()
    af = opts.FILES[0]
    bf = opts.FILES[1] if len(opts.FILES) == 2 else af
    ac = opts.cols[0]
    bc = opts.cols[1]
    infov(opts, 'dataset-1 file: {}'.format(af))
    infov(opts, 'dataset-2 file: {}'.format(bf))
    infov(opts, 'dataset-1 col: {}'.format(ac))
    infov(opts, 'dataset-2 col: {}'.format(bc))
    a = read_file(opts, af, ac)
    b = read_file(opts, bf, bc)
    ttest(a, b, opts)


if __name__ == '__main__':
    main()
