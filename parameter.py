""" Basic classes for nv parameter update. """

import os
import xml.dom.minidom as minidom
from xml.parsers.expat import ExpatError

from nv import NVAutomation, NVAutomationError


class NVParameterError(Exception):
    ''' Raise when something goes wrong.
    '''


class NVParameter(NVAutomation):
    ''' Class to implement the basic nv parameter functionalities.
    '''
    def __init__(self, input_file, target_xml_file, definition_file):
        '''Initialization method.

        input_file      : Input xml file containing NvItems.
        target_xml_file : Source file requested to be updated.
        definition_file : xml file having definitions of NvItems.
        '''
        super(NVParameter, self).__init__(definition_file, input_file, None)
        self.target_xml_file = target_xml_file
        self.xml_doc = minidom.Document()

    def parse(self, parse_file):
        '''Function to parse the xml file.

        parse_file   : xml file needed to be parsed.
        return:
        parsed_doc   : Whole parsed document.
        parsed_items : A list of NvItems parsed by tag name "NvItem"
        '''
        try:
            parsed_doc = minidom.parse(parse_file)
        except ExpatError as err:
            raise NVParameterError("Error in parsing the %s file: %s" %
                                   (parse_file, err))
        except IOError as err:
            raise NVParameterError("Error in reading the %s file: %s" %
                                   (parse_file, err))
        parsed_items = parsed_doc.getElementsByTagName("NvItem")
        return (parsed_doc, parsed_items)

    def write(self):
        '''Function to write to source file with proper indentation.

        target_xml_file : Source file requested to be updated.
        xml_doc         : minidom's xml document element.
        '''
        try:
            with open(self.target_xml_file, 'w') as f:
                self.xml_doc.writexml(f, indent="", addindent="  ", newl="\n")
        except IOError as err:
            raise NVParameterError("Error while writing to %s file: %s" %
                                   (self.target_xml_file, err))

    def copy_existing(self, nvid, target_items, root_element):
        '''Function to copy the NvItems that do not need updating from
        target_items list and append them as child to root_element.

        nvid         : Id attribute of an NvItem.
        target_items : List of NvItems.
        root_element : First and only child of xml_doc.
        '''
        for target_item in target_items:
            try:
                target_nvid = target_item.getAttribute('id')
                if nvid == int(target_nvid):
                    #Strip the nodeValue to remove extra paddings, if any.
                    target_value = target_item.firstChild.nodeValue.strip()
                    target_item.firstChild.nodeValue = target_value
                    root_element.appendChild(target_item)
            except (ValueError, AttributeError) as err:
                raise NVParameterError("Invalid NV item found: %s" % err)

    def find_unique(self, first_nvids, second_nvids):
        '''Function to identify the NV Ids that are present in first_nvids
        list but not in the second_nvids list.

        first_nvids  : List of Nv Ids.
        second_nvids : List of Nv Ids.
        return:
        list_uniq    : List of NV Ids.
        '''
        return list(set(first_nvids).difference(set(second_nvids)))
