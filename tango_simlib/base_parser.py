import abc

class Parser(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        """Parser class handling a simulator description datafile.

        Creating an instance of this class requires calling :meth:`parse`
        afterwards to extract all the provided tango attributes, commands,
        device property and device override class information from the specified
        file.  The formatted data is a dict structure and can be obtained using
        :meth:`get_device_attribute_metadata`,
        :meth:`get_device_command_metadata`,
        :meth:`get_device_properties_metadata` and
        :meth:`get_device_cmd_override_metadata`

        """
        self.data_description_file_name = ''
        self.device_class_name = ''
        self._device_attributes = {}
        self._device_commands = {}
        self._device_properties = {}

    @abc.abstractmethod
    def parse(self, data_file):
        pass
    
    @abc.abstractmethod
    def get_device_attribute_metadata(self):
        pass

    @abc.abstractmethod
    def get_device_command_metadata(self):
        pass

    @abc.abstractmethod
    def get_device_properties_metadata(self, property_group):
        pass
    
    abc.abstractmethod
    def get_device_cmd_override_metadata(self):
        pass