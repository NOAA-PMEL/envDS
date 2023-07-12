from jinja2 import Environment, PackageLoader, select_autoescape

metadata = {
        "attributes": {
            # "name": {"type"mock1",
            "make": {"type": "char", "data": "MockCo"},
            "model": {"type": "char", "data": "Mock1"},
            "description": {
                "type": "char",
                "data": "Simulates a meterological type of sensor for the purposes of testing. Data records are emitted once per second.",
            },
            "tags": {"type": "char", "data": "testing, mock, meteorology, sensor"},
            "format_version": {"type": "char", "data": "1.0.0"},
        },
        "variables": {
            "time": {
                "type": "str",
                "shape": ["time"],
                "attributes": {"long_name": "Time"},
            },
            "temperature": {
                "type": "float",
                "shape": ["time"],
                "attributes": {"long_name": "Temperature", "units": "degree_C"},
            },
            "rh": {
                "type": "float",
                "shape": ["time"],
                "attributes": {"long_name": "RH", "units": "percent"},
            },
            "pressure": {
                "type": "float",
                "shape": ["time"],
                "attributes": {"long_name": "Pressure", "units": "hPa"},
            },
            "wind_speed": {
                "type": "float",
                "shape": ["time"],
                "attributes": {"long_name": "Wind Speed", "units": "m s-1"},
            },
            "wind_direction": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": "Wind Direction",
                    "units": "degree",
                    "valid_min": 0.0,
                    "valid_max": 360.0,
                },
            },
            "flow_rate": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": "Flow Rate",
                    "units": "l min-1",
                    "valid_min": 0.0,
                    "valid_max": 5.0,
                },
            },
        },
        "settings": {
            "flow_rate": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": "Flow Rate",
                    "units": "l min-1",
                    "valid_min": 0.0,
                    "valid_max": 5.0,
                },
            },
        },
    }


env = Environment(
    loader=PackageLoader("test_jinja"),
    autoescape=select_autoescape()
)

template = env.get_template("Make_Model_Version_dataset.xml")
# print(template)

# Use version.major as identifier, all other version changes should be backward compatible
# print(metadata["attributes"]) #["format_version"]["data"])
# exit()
version = f'v{metadata["attributes"]["format_version"]["data"].split(".")[0]}'

ds_context = {
    "make": metadata["attributes"]["make"]["data"],
    "model": metadata["attributes"]["model"]["data"],
    "version": version,
    "description": metadata["attributes"]["description"]["data"],
}

# vars_context = []
var_template = env.get_template("Make_Model_Version_variable.xml")
variables = []
for name, variable in metadata["variables"].items():

    if name == "time":
        continue

    var_context = dict()
    var_context["source_name"] = name
    var_context["destination_name"] = name
    var_context["data_type"] = variable["type"]

    # missing_value = "NaN"
    # if variable["type"] == "int":
    #     missing_value = "NaN"
    # elif variable["type"] == "string":
    #     missing_value = "NaN"
    # var_context["missing_value"] = missing_value

    if "long_name" in variable["attributes"]:
        var_context["long_name"] = variable["attributes"]["long_name"]
    else:
        var_context["long_name"] = name.capitalize()

    if "units" in variable["attributes"]:
         var_context["units"] = variable["attributes"]["units"]

    if "valid_min" in variable["attributes"]:
         var_context["valid_min"] = variable["attributes"]["valid_min"]

    if "valid_max" in variable["attributes"]:
         var_context["valid_max"] = variable["attributes"]["valid_max"]

    if "description" in variable["attributes"]:
         var_context["description"] = variable["attributes"]["description"]

    variables.append(
        var_template.render(variable=var_context)
    )
    # print(var_context)
    print(var_template.render(variable=var_context))
# print(variables)
# print(template.render(dataset=ds_context, variables=variables))
out = template.render(dataset=ds_context, variables=variables)
with open("test.xml", "w") as f:
    f.write(out)
