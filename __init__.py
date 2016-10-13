""" nv automation module including nv verification automation
and nv update automation. It contains only the common code.
"""
import uuid
import xml.dom.minidom
from xml.parsers.expat import ExpatError

NEW_DEFINITION_FILE = "new_definition_%s.xml"

NV_TYPE_EFS = "EFS"
NV_TYPE_EFS_RANGE = 65535
NV_TYPE_ETS = "ETS"
NV_TYPE_TA = "TA"
NV_TYPE_NV = "NV"


class NVItem(object):
    '''Class to hold the nv item attribute and values.
    '''
    def __init__(self, nv_id, nv_name, nv_values, nv_type=NV_TYPE_NV):
        '''Initialization.

        nv_id    : id field in NvItem, int type.
        nv_name  : name field in NvItem, string type.
        nv_values: NvItem value, comma separated values as string.
        nv_type  : Type of nv item. It can be EFS, TA, ETS or normal NV.
        '''
        self.nv_id = nv_id
        self.nv_name = nv_name
        self.nv_values = nv_values
        self.nv_type = nv_type


class NVAutomationError(Exception):
    ''' Raise when something goes wrong
    '''


class NVAutomation(object):
    ''' Base class for NV Verification automation. Common implementations
    are here.
    '''
    def __init__(self, definition_file, input_file, port):
        ''' Initialization method.

        Arguments:
        definition_file : definition file for reading NV value.
        input_file      : input file for generating the new definition file
                          and for the verification purpose.
        port            : port number that is connected into the phone.
        '''
        self.definition_file = definition_file
        self.input_file = input_file
        self.connection_port = port
        # Need to make a unique random filename to avoid conflicts with other
        #file (if any)
        self.new_def_file = NEW_DEFINITION_FILE % uuid.uuid4()

    def read_input_file(self, nv_file=None):
        ''' Read all the input NV ids from input file and return as a list.

        nv_file: Input nv file to read. It will read default input_file if
                 nv_file is not provided.

        return: returns only the nv id of NvItem.
        '''
        input_nv_ids = []

        if not nv_file:
            nv_file = self.input_file

        nv_items = self._read_nv_items(nv_file)
        for nv_item in nv_items:
            # first item is the nv_id
            input_nv_ids.append(nv_item.nv_id)

        return input_nv_ids

    def _get_nv_type(self, nv_id, nv_calibrated):
        ''' Get the NV type based on nv id and nv calibrated attribute value.

        nv_id: nv id no.
        nv_calibrated: nv calibrated. There can be 3 types of values, 'true',
                       'false' and 'ets'.
        '''
        nv_type = NV_TYPE_NV

        if nv_calibrated.strip().lower() == "true":
            nv_type = NV_TYPE_TA
        elif nv_calibrated.strip().lower() == "ets":
            nv_type = NV_TYPE_ETS

        if nv_id > NV_TYPE_EFS_RANGE:
            nv_type = NV_TYPE_EFS

        return nv_type

    def _read_nv_items(self, nv_file):
        '''Read the nv file and collect the id, name and values of NvItem.
        In default implementation it will read the xml file. User can override
        this behavior, for example using the text file.

        nv_file: nv xml file to parse. This have <NvItem> tag.
        return: Returns the list of nv items (NVItem object in the list)
        '''
        nv_items = []

        try:
            dom = xml.dom.minidom.parse(nv_file)
        except ExpatError as err:
            raise NVAutomationError("Error in parsing the input file: %s"
                                    % err)
        except IOError as err:
            raise NVAutomationError("IOError: %s" % err)

        for tag in dom.getElementsByTagName('NvItem'):
            nv_id = tag.getAttribute("id")
            nv_name = tag.getAttribute("name")
            nv_values = tag.childNodes[0].nodeValue
            nv_calibrated = tag.getAttribute("calibrated")

            try:
                nv_items.append(NVItem(int(nv_id), nv_name.strip(),
                                       nv_values.strip(),
                                       self._get_nv_type(int(nv_id),
                                                         nv_calibrated)))
            except TypeError as err:
                raise NVAutomationError("Invalid type NV item found: %s" % err)
            except ValueError as err:
                raise NVAutomationError("Invalid NV item found: %s" % err)
            except AttributeError as err:
                raise NVAutomationError("Invalid NV item found: %s" % err)

        return nv_items

    def create_new_definition_file(self):
        '''Read the definition file and generate a new definition file based on
        the input nv items.

        We need the definition file to read the nv items from the phone using
        the QCT tool. Basically it reads all the nv items based on the
        definition file. But the original definition file is really big and it
        takes more time to read the nv items. So we need a new minimal
        definition file based on the input nv items that actually required.

        return:
        This function will return the newly created definition file name.
        '''
        input_nv_id_list = self.read_input_file()

        try:
            dom = xml.dom.minidom.parse(self.definition_file)
        except ExpatError as err:
            raise NVAutomationError("Error in parsing the definition file: %s"
                                    % err)
        except IOError as err:
            raise NVAutomationError("Error in reading definition file: %s"
                                    % err)

        #If any of following operation fails, we don't need further operation.
        try:
            new_xml_doc = xml.dom.minidom.Document()
            root_tag = new_xml_doc.createElement('NvDefinition')
            new_xml_doc.appendChild(root_tag)

            #Also require to include all the <DataType> tags from the
            #definition file. These are user defined data types that can be
            #used in NvItem
            for tag in dom.getElementsByTagName("DataType"):
                root_tag.appendChild(tag)

            for tag in dom.getElementsByTagName("NvItem"):
                tag_id = tag.getAttribute("id")
                for nv_id in input_nv_id_list:
                    if(nv_id == int(tag_id)):
                        root_tag.appendChild(tag)

            with open(self.new_def_file, 'w') as fp_xml:
                new_xml_doc.writexml(fp_xml)
        except TypeError as err:
            raise NVAutomationError("Invalid type nv item found: %s" % err)
        except ValueError as err:
            raise NVAutomationError("Invalid nv item found: %s" % err)
        except AttributeError as err:
            raise NVAutomationError("Error in creating new definition file: %s"
                                    % err)
        except IOError as err:
            raise NVAutomationError("Error in creating new definition file: %s"
                                    % err)
        except Exception as err:
            raise NVAutomationError("Unknown error in creating new definition"
                                    "file: %s" % err)

    def _update_nv_items_with_def_file(self, input_nv_item_list):
        ''' Update the nv_type with the definition nv_type.

        input_nv_item_list: nv item list that needs to be updated with the
                            definition nv items.
        '''
        def_nv_item_list = self._read_nv_items(self.new_def_file)

        for nv_item in input_nv_item_list:
            for def_nv_item in def_nv_item_list:
                if (nv_item.nv_id == def_nv_item.nv_id and
                        nv_item.nv_name == def_nv_item.nv_name):
                    nv_item.nv_type = def_nv_item.nv_type
                    break

        return input_nv_item_list
