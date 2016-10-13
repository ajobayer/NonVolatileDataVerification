#!/usr/bin/env python
""" Classes for NV Verification Automation. Windows(QCT) and Linux(ETS) will
be implemented in the same file.
"""
import logging
import optparse
import os
import processes
import re

from nv import NVAutomation, NVAutomationError, NVItem

QCT_COMMAND_TOOL_NAME = "qmsl_nvtool_msvc7r.exe"

REPORT_FILE = "verification_report.html"
REPORT_TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "verification_report_template.txt")

DEFAULT_NV_DEFINITION_FILE = "definition.xml"
DEFAULT_NV_INPUT_FILE = "input.xml"
DEFAULT_NV_OUT_FILE = "nv_out.xml"

RESULT_OK = "OK"
RESULT_NG = "NG"
RESULT_PASSED = "<span style='color:green;'>PASSED</span>"
RESULT_FAILED = "<span style='color:red;'>FAILED</span>"
RESULT_SKIPPED = "<span style='color:gray;'>SKIPPED</span>"
REPORT_SUMMARY_PASSED = "<span style='color:green;'>PASSED</span>"
REPORT_SUMMARY_FAILED = "<span style='color:red;'>FAILED</span>"

NV_TYPE_EFS = "EFS"
NV_TYPE_EFS_RANGE = 65535
NV_TYPE_ETS = "ETS"
NV_TYPE_TA = "TA"
NV_TYPE_NV = "NV"


def command_tool_exists(command_tool):
    ''' Check the command tool in the PATH variable. In QCT tools based
    verification we need to run the command in backend. But this implementation
    is kept as generic. So both in Linux and Windows based system this method
    can be used.
    '''

    def is_exe(fpath):
        #print os.access(fpath, os.X_OK)
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    PATH = os.environ["PATH"].split(os.pathsep)
    for p in PATH:
        #print os.path.join(p, command_tool)
        if is_exe(os.path.join(p, command_tool)):
            return True

    return False


class VerificationItem(object):
    '''Class to hold the verification items and result together.
    '''
    def __init__(self, input_nv_item, output_nv_item, result):
        '''Initialization.

        input_nv_item: input nv item that already checked.
        output_nv_item: output nv item that already checked.
        result: checked result between input and output nv items
                (OK or NG)
        '''
        self.input_nv_item = input_nv_item
        self.output_nv_item = output_nv_item
        self.verification_result = result


class NVAutomationQCT(NVAutomation):
    ''' NV Verification Automation for windows based system.
    '''
    def __init__(self, definition_file, input_file, port,
                 out_file=DEFAULT_NV_OUT_FILE):
        #Call the base class constructor
        super(NVAutomationQCT, self).__init__(
            definition_file, input_file, port)
        #define its own property, specific to windows based
        self.command_tool = QCT_COMMAND_TOOL_NAME
        self.out_file = out_file

    def verify(self, report_file=None):
        '''Verify the nv items of input and output and publish the report.

        report_file: whether to save the verification result in a file.
                     If the file is given it will be saved otherwise not.
        '''
        verification_result_list = []
        input_nv_items = self._update_nv_items_with_def_file(
            self._read_nv_items(self.input_file))
        output_nv_items = self._read_nv_items(self.out_file)

        if not input_nv_items or not output_nv_items:
            raise NVAutomationError("Can't verify. "
                                    "Problem in input or output nv items.")
        for in_nv_item in input_nv_items:
            found_matched_in_nv_item = False
            for out_nv_item in output_nv_items:
                if (in_nv_item.nv_id == out_nv_item.nv_id and
                        in_nv_item.nv_name == out_nv_item.nv_name):
                    found_matched_in_nv_item = True
                    break
            if found_matched_in_nv_item:
                if in_nv_item.nv_values == out_nv_item.nv_values:
                    verification_item = VerificationItem(in_nv_item,
                                                         out_nv_item,
                                                         RESULT_OK)
                else:
                    verification_item = VerificationItem(in_nv_item,
                                                         out_nv_item,
                                                         RESULT_NG)
                verification_result_list.append(verification_item)
            # if input nv item found but output nv item not found
            # we will put empty data for the output nv item in the list
            else:
                verification_item = VerificationItem(in_nv_item,
                                                     NVItem(-1, "", ""),
                                                     RESULT_NG)
                verification_result_list.append(verification_item)

        if report_file:
            self.publish_verification_result(verification_result_list,
                                             report_file)

        return verification_result_list

    def _read_report_template(self, report_template_file=REPORT_TEMPLATE_FILE):
        ''' Read the template text from the template file.

        report_template_file: template file to parse.

        return: Returns the template text for report header, values and footer.
        '''
        try:
            with open(report_template_file) as tem_fp:
                for line in tem_fp.readlines():
                    if re.search(r'%header%', line):
                        report_header = line.strip().replace("%header%", "")
                    elif re.search(r'%values%', line):
                        report_values = line.strip().replace("%values%", "")
                    elif re.search(r'%footer%', line):
                        report_footer = line.strip().replace("%footer%", "")
        except IOError as err:
            raise NVAutomationError("Unable to read the template file: %s" %
                                    err)

        return report_header, report_values, report_footer

    def publish_verification_result(self, result_list,
                                    report_file=REPORT_FILE):
        '''Simple report to publish the verification result.

        result_list: verification result list
        report_file: filename to save the verification result.
        '''
        summary = REPORT_SUMMARY_PASSED
        # if we find the empty list the verification result will be NG
        if not result_list:
            summary = REPORT_SUMMARY_FAILED
        REPORT_HEADER, REPORT_VALUES, REPORT_FOOTER = \
            self._read_report_template()

        try:
            with open(report_file, "w") as fp:
                report_values = ""
                for result in result_list:
                    # If any result is NG the summary will be FAILED.
                    # This is only valid for non EFS, TA or ETS nv items.
                    nv_item_verification_result = RESULT_PASSED
                    if result.input_nv_item.nv_type == NV_TYPE_NV and \
                            result.verification_result == RESULT_NG:
                        nv_item_verification_result = RESULT_FAILED
                        summary = REPORT_SUMMARY_FAILED
                    # For EFS, TA or ETS nv items, it will be skipped.
                    elif result.input_nv_item.nv_type != NV_TYPE_NV:
                        nv_item_verification_result = RESULT_SKIPPED

                    report_values += REPORT_VALUES % (
                        result.input_nv_item.nv_id,
                        result.input_nv_item.nv_values,
                        result.output_nv_item.nv_values,
                        result.input_nv_item.nv_name,
                        result.output_nv_item.nv_name,
                        result.input_nv_item.nv_type,
                        nv_item_verification_result)
                fp.write("%s%s%s" % (REPORT_HEADER, report_values,
                                     REPORT_FOOTER % summary))
        except (IOError, TypeError) as err:
            raise NVAutomationError("Unable to publish the result: %s" % err)

    def read_nv_items_from_phone(self, definition_file):
        '''Read the nv items from phone and store into the output file.

        definition_file: definition file name to use for getting nv items from
                         the phone.

        Exception raised: NVAutomationError, if any problem executing the QCT
                          command tool.
        '''
        if not command_tool_exists(self.command_tool):
            raise NVAutomationError("QCT tool '%s' not found.  Check the "
                                    "path in your environment" %
                                    self.command_tool)
        cmdandargs = [self.command_tool, "-ph2src", "-def=" + definition_file,
                      "-src=" + self.out_file, "-qpst",
                      "-com=" + self.connection_port]
        try:
            result = processes.run_cmd(cmdandargs)
        except processes.ChildExecutionError as err:
            raise NVAutomationError("Unable to run the QCT command tool: %s" %
                                    err)
        # Verify whether the QCT tool itself run without any error
        cmd_failed = re.search(r'Command failed', result[1])
        if cmd_failed:
            raise NVAutomationError("Invalid parameter used in QCT command "
                                    "tool.")


class NVAutomationETS(NVAutomation):
    ''' NV Verification Automation for Linux based system.
    '''


def _main():
    usage = "usage: %prog [-d DEFINITION_FILE] [-i INPUT_FILE]" \
            " [-o OUTPUT_FILE] [-r REPORT_FILE] <-p PORT_NUM>"

    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-d", "--def", action="store",
                      default=DEFAULT_NV_DEFINITION_FILE,
                      dest="definition_file", help="Definition file name.")
    parser.add_option("-i", "--input", action="store",
                      default=DEFAULT_NV_INPUT_FILE,
                      dest="input_file", help="Input file name.")
    parser.add_option("-o", "--output", action="store",
                      default=DEFAULT_NV_OUT_FILE,
                      dest="output_file", help="Output file name.")
    parser.add_option("-r", "--report", action="store", default=None,
                      dest="report_file", help="Report publishing file name.")
    parser.add_option("-p", "--port", action="store", default=None,
                      dest="port_num", help="Connected port number to phone.")

    (options, _args) = parser.parse_args()

    level = logging.DEBUG
    logging.basicConfig(format='[%(levelname)s] %(message)s',
                        level=level)

    if not options.port_num:
        parser.error("You must provide the port number using '-p PORT_NUM'")

    nv_automation = NVAutomationQCT(options.definition_file,
                                    options.input_file, options.port_num,
                                    options.output_file)

    logging.info("Generating the new definition file")
    nv_automation.create_new_definition_file()

    logging.info("Reading nv items from phone on port: %s", options.port_num)
    try:
        nv_automation.read_nv_items_from_phone(nv_automation.new_def_file)
    except NVAutomationError as err:
        try:
            os.remove(nv_automation.new_def_file)
        except OSError:
            pass
        raise NVAutomationError("Unable to read nv items from phone: %s" % err)

    logging.info("Verifying the nv items and publishing report")
    if options.report_file is None:
        # save report in default file
        nv_automation.verify(REPORT_FILE)
        logging.info("Verification result is published in: '%s' file",
                     REPORT_FILE)
    else:
        result_list = nv_automation.verify()
        nv_automation.publish_verification_result(result_list,
                                                  options.report_file)
        logging.info("Verification result is published in: '%s'",
                     options.report_file)

    # After finish, remove the newly created definition file (if any)
    try:
        os.remove(nv_automation.new_def_file)
    except OSError:
        logging.info("Cannot remove the new definition file, please "
                     "remove it manually")

if __name__ == "__main__":
    try:
        _main()
    except NVAutomationError as err:
        raise NVAutomationError("Program exits with following error: %s" % err)
