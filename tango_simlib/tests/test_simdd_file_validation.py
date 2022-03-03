import json
import pkg_resources

from jsonschema import validate


def test_validate_testsim_simdd_file():
    """Check that the Testsim_SimDD.json file conforms to the SimDD.schema"""

    simdd_schema_file = pkg_resources.resource_filename('tango_simlib.utilities', 'SimDD.schema')
    simdd_config_file = pkg_resources.resource_filename('tango_simlib.tests.config_files', 'TestSim_SimDD.json')

    with open(simdd_schema_file) as simdd_schema, open(simdd_config_file) as simdd_file:
        schema_data = json.load(simdd_schema)
        simdd_data = json.load(simdd_file)

        validate(schema_data, simdd_data)
