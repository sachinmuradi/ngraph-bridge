# ==============================================================================
#  Copyright 2018-2019 Intel Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ==============================================================================
import unittest
import sys
import argparse
import os
import re
import fnmatch
import time
from datetime import timedelta
import warnings

try:
    import xmlrunner
except:
    os.system('pip install unittest-xml-reporting')
    import xmlrunner
"""
tf_unittest_runner is primarily used to run tensorflow python 
unit tests using ngraph
"""


def main():
    parser = argparse.ArgumentParser()
    optional = parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')

    required.add_argument(
        '--tensorflow_path',
        help=
        "Specify the path to Tensorflow source code. Eg:/localdisk/skantama/tf-ngraph/tensorflow \n",
        required=True)
    optional.add_argument(
        '--list_tests',
        help="Prints the list of test cases in this package. Eg:math_ops_test \n"
    )
    optional.add_argument(
        '--run_test',
        help=
        "Runs the testcase and returns the output. Eg:math_ops_test.DivNoNanTest.testBasic"
    )
    optional.add_argument(
        '--run_tests_from_file',
        help="""Reads the test names specified in a file and runs them. 
        Eg:--run_tests_from_file=tests_to_run.txt""")
    optional.add_argument(
        '--xml_report',
        help=
        "Generates results in xml file for jenkins to populate in the test result \n"
    )
    optional.add_argument(
        '--verbose',
        action="store_true",
        help="Prints standard out if specified \n")
    parser._action_groups.append(optional)
    arguments = parser.parse_args()

    xml_report = arguments.xml_report
    if (arguments.list_tests):
        test_list = get_test_list(arguments.tensorflow_path,
                                  arguments.list_tests)
        print('\n'.join(test_list[0]))
        return None, None

    if (arguments.run_test):
        start = time.time()
        test_list = get_test_list(arguments.tensorflow_path, arguments.run_test)
        test_results = run_test(test_list[0], xml_report)
        elapsed = time.time() - start
        print("Testing results\nTime elapsed: ", str(
            timedelta(seconds=elapsed)))
        return check_and_print_summary(test_results)

    if (arguments.run_tests_from_file):
        all_test_list = []
        invalid_list = []
        start = time.time()
        list_of_tests = read_tests_from_file(arguments.run_tests_from_file)
        for test in list_of_tests:
            test_list = get_test_list(arguments.tensorflow_path, test)
            for test in test_list[1]:
                if test is not None:
                    invalid_list.append(test_list[1])
            test_list = list(set(test_list[0]))
            for test_name in test_list:
                if test_name not in all_test_list:
                    all_test_list.append(test_name)
        test_results = run_test(all_test_list, xml_report)
        elapsed = time.time() - start
        print("Testing results\nTime elapsed: ", str(
            timedelta(seconds=elapsed)))
        return check_and_print_summary(test_results)


def check_and_print_summary(test_results):
    print("TOTAL: ", len(test_results['TOTAL']))
    print("PASSED: ", len(test_results['PASSED']))
    print("FAILED: ", len(test_results['FAILED']))
    if len(test_results['FAILED']) == 0:
        return True
    else:
        return False


def get_test_list(tf_path, test_regex):
    accepted_formats = [
        "math_ops_test", "mat_ops_test.DivNoNanTest",
        "math_ops_test.DivNoNanTest.testBasic", "math_ops_test.DivNoNanTest.*",
        "math_ops_test.D*", "math_ops_test.*", "math_*_test", "math_*_*_test",
        "math*_test"
    ]
    try:
        module_list = regex_walk(tf_path, test_regex)
    except Exception as e:
        module_list = []
        print(
            "Exception occured in regex_walk. " + str(e) +
            """\nInvalid module name. Use bazel query below to get list of tensorflow python test modules.
            bazel query 'kind(".*_test rule", //tensorflow/python:nn_test)' --output label\n"""
        )
    try:
        test_list = list_tests(module_list, test_regex)
    except Exception as e:
        test_list = [[], []]
        print(
            "Exception occured in list_tests. " + str(e) +
            "\nEnter a valid argument to --list_tests or --run_test.\n \nLIST OF ACCEPTED FORMATS:"
        )
        print('\n'.join(accepted_formats))
    return test_list


from fnmatch import fnmatch


def regex_walk(dirname, regex_input):
    """
    Adds all the directories under the specified dirname to the system path to 
    be able to import the modules.
    
    Args:
    dirname: This is the tensorflow_path passed as an argument is the path to 
    tensorflow source code.
    
    regex_input: Regular expression input string to filter and list/run tests.
    Few examples of accepted regex_input are:
    math_ops_test
    math_ops_test.DivNanTest
    math_ops_test.DivNoNanTest.testBasic
    math_ops_test.DivNoNanTest.*
    math_ops_test.D*
    math_ops_test.*
    math_*_test
    math_*_*_test
    math*_test
    """
    if (re.search("\.", regex_input) is None):
        test = regex_input + '.py'
    else:
        test = (re.split("\.", regex_input))[0] + '.py'
    module_list = []
    for path, subdirs, files in os.walk(dirname):
        for name in files:
            if fnmatch(name, test):
                sys.path.append(path)
                name = os.path.splitext(name)[0]
                module_list.append(name)
    if not module_list:
        sys.exit(1)
    return module_list


def list_tests(module_list, regex_input):
    """
    Generates a list of test suites and test cases from a TF test target 
    specified. 

    Args:
    module_list: This is a list tensorflow test target names passed as an argument.
    Example --list_tests=math_ops_test.R*
    To get the list of tensorflow python test modules, query using bazel.
    bazel query 'kind(".*_test rule", //tensorflow/python/...)' --output label

    regex_input: Regular expression input strings to filter and list tests. 
    Few examples of accepted regex_input are:
    math_ops_test
    math_ops_test.DivNanTest
    math_ops_test.DivNoNanTest.testBasic
    math_ops_test.DivNoNanTest.*
    math_ops_test.D*
    math_ops_test.*
    math_*_test
    math_*_*_test
    math*_test
    """
    loader = unittest.TestLoader()
    alltests = []
    for test_module in module_list:
        module = __import__(test_module)
        if (module is None):
            print("Enter a valid test name to run")
        test_modules = loader.loadTestsFromModule(module)
        for test_class in test_modules:
            for i in test_class:
                alltests.append(i.id())

    if (re.search("\.", regex_input) is None):
        return alltests, []
    else:
        test_name = (re.split("\*", regex_input))[0]
        listtests = []
        invalidtests = []
        for test in alltests:
            if test_name in test:
                listtests.append(test)
        if not listtests:
            invalidtests.append(regex_input)
        return listtests, invalidtests


def read_tests_from_file(filename):
    with open(filename) as list_of_tests:
        return [
            line.split('#')[0].rstrip('\n').strip(' ')
            for line in list_of_tests.readlines()
            if line[0] != '#' and line != '\n'
        ]


def run_test(test_list, xml_report, verbosity=0):
    """
    Runs a specific test suite or test case given with the fully qualified 
    test name and prints stdout.

    Args:
    test_list: This is the list of tests to run,filtered based on the 
    regex_input passed as an argument.
    Example: --run_test=math_ops_test.A*   
    verbosity: Python verbose logging is set to 2. You get the help string 
    of every test and the result.
    """
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    succeeded = []
    failures = []
    if xml_report is not None:
        for test in test_list:
            names = loader.loadTestsFromName(test)
            suite.addTest(names)
        with open(xml_report, 'wb') as output:
            sys.stdout = open(os.devnull, "w")
            sys.stderr = open(os.devnull, "w")
            test_result = xmlrunner.XMLTestRunner(
                output=output, verbosity=verbosity).run(suite)
            sys.stderr = sys.__stderr__
            sys.stdout = sys.__stdout__
            failures.extend(test_result.failures)
            failures.extend(test_result.errors)
            succeeded.extend(test_result.successes)

        summary = {"TOTAL": test_list, "PASSED": succeeded, "FAILED": failures}
        return summary
    else:
        for test in test_list:
            start = time.time()
            sys.stdout = open(os.devnull, "w")
            sys.stderr = open(os.devnull, "w")

            test_result = unittest.TextTestRunner(verbosity=verbosity).run(
                loader.loadTestsFromName(test))

            sys.stderr = sys.__stderr__
            sys.stdout = sys.__stdout__
            elapsed = time.time() - start
            elapsed = str(timedelta(seconds=elapsed))

            if test_result.wasSuccessful():
                succeeded.append(test)
                result_str = " \033[92m OK \033[0m " + test
            elif test_result.failures:
                failures.append(test_result.failures)
                result_str = " \033[91m FAIL \033[0m " + test + \
                    '\n\033[91m' + ''.join(test_result.failures[0][1]) + '\033[0m'
            elif test_result.errors:
                failures.append(test_result.errors)
                result_str = " \033[91m FAIL \033[0m " + test + \
                    '\n\033[91m' + ''.join(test_result.errors[0][1]) + '\033[0m'
            print('TEST: ', elapsed, result_str)
        summary = {"TOTAL": test_list, "PASSED": succeeded, "FAILED": failures}
        return summary


def print_and_check_results(test_result, invalid_list, verbose):
    """
    Prints the results of the tests run and the stats.
    Prints the list of invalid tests if any.

    Args:
    test_result: This is a list of test cases that ran along with their 
    status Pass, Fail or Error. 
    invalid_list: When tests are run from file, if there is an invalid test 
    name this list is printed along with summary.
    """
    status = True
    print('\033[1m' + '\n==SUMMARY==' + '\033[0m')
    for key in ["PASSED", "FAILED"]:
        test_name = test_result[key]
        for test in test_name:
            if verbose and key is "PASSED":
                print(test + '\033[92m' + ' ..PASS' + '\033[0m')
            if key is "FAILED":
                print(test[0][0].id() + '\033[91m' + ' ..FAIL' + '\033[0m')
                print(test[0][1])

    if verbose and (len(invalid_list) != 0):
        print('\033[1m' + '\nInvalid Tests' + '\033[0m')
        print('\n'.join(' '.join(map(str, test)) for test in invalid_list))

    if verbose:
        print('\033[1m' + '\n==STATS==' + '\033[0m')
    for key in ["PASSED", "FAILED"]:
        test_class_name = {}
        test_case_name = {}
        test_name = test_result[key]
        for test in test_name:
            if key is "PASSED":
                module, classname, testcase = test.split('.')
                module_classname = module + '.' + classname
                test_class_name[module_classname] = test_class_name.get(
                    module_classname, 0) + 1
                test_case_name[test] = test_case_name.get(test, 0) + 1
            if key is "FAILED":
                status = False
                module, classname, testcase = test[0][0].id().split('.')
                module_classname = module + '.' + classname
                test_class_name[module_classname] = test_class_name.get(
                    module_classname, 0) + 1
                test_case_name[test[0][0]] = test_case_name.get(test[0][0],
                                                                0) + 1
        if verbose:
            for k in test_class_name:
                print('Number of tests ' + key + ' ' + k, test_class_name[k])
        else:
            color = {
                'PASSED': '\033[98m',
                'FAILED': '\033[91m',
            }[key]
            if len(test_case_name.keys()) > 0:
                print('Number of tests ' + color + key + ' ' + '\033[0m' +
                      str(len(test_case_name.keys())))

    return status


if __name__ == '__main__':
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        status = main()
        if status == False:
            raise Exception("Tests failed")
