# cmpds
Compare two datasets to determine whether there is a significant difference between them for a specific confidence level
using the t-test methodology for unpaired observations.

> Please note that this is not, strictly, a t-test because it switches
> over to the standard normal distribution (SND) when the number of
> effective degrees of freedom (DOF) is larger than 32.

It is really useful for determining whether runtime or memory use has
changed between two different versions of software. The datasets are
completely independent of the program (i.e. the data values are created by tools
like /usr/bin/time) so they can be used in a black box testing environment.

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

## Download
Here are the steps to download cmpds to your system.
```bash
$ git clone https://github.com/jlinoff/cmpds.git
$ ./cmpds.py -h
```

There is a test directory that contains a Makefile, a test script (test.sh)
and some sample data for testing. To use it, cd to the test directory
and type `make`.

```bash
$ cd test
$ make

test no change
With 95.0% confidence, there is no significant difference between the datasets.
test:01:043: passed - no change

test dataset-2 is smaller, CL=95%
With 95.0% confidence, dataset-2 is smaller than dataset-1 by about 1.7%.
test:02:057: passed - dataset-2 is smaller, CL=95%

test dataset-2 is larger, CL=95%
With 95.0% confidence, dataset-2 is larger than dataset-1 by about 1.8%.
test:03:071: passed - dataset-2 is larger, CL=95%

test dataset-2 is smaller, CL=90%
With 90.0% confidence, dataset-2 is smaller than dataset-1 by about 1.6%.
test:04:085: passed - dataset-2 is smaller, CL=90%

test dataset-2 is larger, CL=90%
With 90.0% confidence, dataset-2 is larger than dataset-1 by about 1.6%.
test:05:099: passed - dataset-2 is larger, CL=90%

test exmple-1 two datasets in one file
With 95.0% confidence, dataset-2 is smaller than dataset-1 by about 1.1%.
test:06:110: passed - exmple-1 two datasets in one file

test:summary passed  6
test:summary failed  0
test:summary total   6
PASSED
```

This tool has been tested on Mac OS X 10.11.6 and CentOS 7.2. It should run on any linux or BSD unix system.
It will also probably run on Windows systems but I am unable to test that because I don't have one available.

## Example 1 - two datasets in one file

Here is an example to make sense of it all.

We want to compare two versions of the foobar program to see if the
second version is faster than the first for the same inputs. The
versions are 1.1 and 1.2. The program takes about 2 minutes to run
(120 seconds) and we want to determine whether v1.2 is faster.
The table below shows sample data 10 runs for each version.

```bash
$ cat example1.ds
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
```

For this example we assume that the data is stored in a single file
but normally it is easier to have it exist in two separate files
because, by default, the tool looks at the first token on each line
and collects it if the token is a floating point number. When the data
is not in a single column in a file, you must explicitly specify the
which column to collect. In this case, the first dataset is in column
2 and the second dataset is in column 3 of the same file. Blank lines
and lines where the token is not a floating point number are ignored.

Here is what the run looks like:

```bash
$ ./cmpds.py -c 0.95 -k 2 3 data.txt
With 95.0% confidence, dataset-2 is smaller than dataset-1 by about 1.1%.
```
As you can see, dataset-2 (v1.2) is slightly faster.

> Note that we use -k to specify the columns because -c is already reserved for
> specifying the confidence level.

If you reverse the columns, you will get the opposite result:
```bash
$ ./cmpds.py -c 0.95 -k 3 2 data.txt
With 95.0% confidence, dataset-2 is larger than dataset-1 by about 1.1%.
```

> We use -k to specify the columns because -c is already reserved for
> specifying the confidence level.

## Example 2 - datasets in separate files
A more realistic example would be running a program called blackbox-v1
50 times and collecting the timing output to a file and then running
blackbox-v2 and collecting its output. Here is how you might do it:

```bash
$ rm -f /tmp/blackbox-v1.out /tmp/blackbox-v2.out
$ for((i=1;i<=50;i++)) ; do printf '\nExp %03d\n' $i ; /usr/bin/time -p blackbox-v1 >> /tmp/v1.out ; done
$ for((i=1;i<=50;i++)) ; do printf '\nExp %03d\n' $i ; /usr/bin/time -p blackbox-v2 >> /tmp/v2.out ; done
```

We can now capture the real run time data by simply grepping out the
data like this:

```bash
$ grep -w ^real /tmp/v1.out > /tmp/v1.ds
$ grep -w ^real /tmp/v2.out > /tmp/v2.ds
```

The above command takes advantage of the fact that posix time format
(-p) outputs the time data on 3 separate lines as shown in this simple
example:

```bash
$ /usr/bin/time -p sleep 0.3
real         0.30
user         0.00
sys          0.00
```

At this point we have the unpaired observations from both runs in two
different files so we can use cmpds.py to figure out whether v2 is
faster than v1 at a 95% confidence level.

```bash
$ ./cmpds.py -c 0.95 /tmp/v1.ds /tmp/v2.ds
With 95.0% confidence, dataset-2 is smaller than dataset-1 by about 1.3%.
```

That tells us that v2 is indeed slightly faster.

## Program arguments
The program requires that you specify one or two dataset files as input.
In addition there are a number optional arguments.
They are shown in the table below.

| Short Form | Long Form    | Description |
| :--------- | :----------- | :---------- |
| -c FLOAT   | --conf FLOAT | The confidence level such that 0 < c < 1.<br>The default is 0.95. |
| -h         | --help       | Show the help message and exit. |
| | --internal T L U I | Factors used for internal compution.<br>You normally do not need to change these.<br>See the actual help for more details |
| -k COL1 COL2 | --cols COL1 COL2 | The columns that define each dataset.<br>The first column is for the first dataset.<br>The second column is for the second dataset.<br>If the value in the column is not a floating point number it is ignored.
| -s UINT | --snd-threshold UINT | The standard normal distribution (SND) threshold.<br>When the number of effective degrees of freedom (DOF)<br>exceeds this threshold, the SND is used instead of a<br>t-distribution.|
| -v | --verbose | Increase the level of verbosity.<br>Specify -v to see the values that make up the computation.<br>Specify -v -v to internal details about the z value lookup and<br>values that were discarded during file reads.|
| -V | --version | Show program's version number and exit. |

## Feedback
Any feedback or suggestions to improve the approach are greatly appreciated.

Enjoy!
