import json
import re

def infer_type(value):
    """ Determine correct type: int, float, None, or char """
    if value.lower() == "null":
        return "None"
    elif value.isdigit():
        return "int"
    else:
        try:
            float(value)
            return "float"
        except ValueError:
            return "char"

def convert_type(value):
    """ Convert string to correct type (int, float, None, or str) """
    if value.lower() == "null":
        return None  # Convert "null" to Python None
    elif value.isdigit():
        return int(value)  # Convert whole numbers to int
    else:
        try:
            return float(value)  # Convert valid float strings
        except ValueError:
            return value.strip('"')  # Remove quotes and keep as string

def extract_rawx_sections(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    rawx_sections = []
    recording = False
    current_section = []

    for i, line in enumerate(lines):
        temp = []
        if "RAWX Data Table Format" in lines[i]:
            i += 1
            if '{' in lines[i]:
                bracket_stack = 1
                temp.append(lines[i])
            else:
                bracket_stack = 0
            
            while bracket_stack > 0:
                i += 1
                if '{' in lines[i]:
                    bracket_stack += 1
                if '}' in lines[i]:
                    bracket_stack -= 1
                temp.append(lines[i])
            rawx_sections.append(temp)        

    return rawx_sections

def ea_formater(rawx_sections):
    jsons = []
    for i, section in enumerate(rawx_data_list, 1):
        if len(section) == 0:
            continue
        class_name = section[0].split(":")[0]

        # loop untile find "fields"
        j = 0
        while "fields" not in section[j]:
            j += 1
        attribute_names = []
        while "],\n" not in section[j]:
            if "fields" in section[j]:
                attributes = section[j].split(":[")[1]
            else:
                attributes = section[j]
            for attribute in attributes.split(','):
                if attribute != "\n":
                    attribute_names.append(attribute.strip())
            j+=1
        
        if "fields" in section[j]:
            attributes = section[j].split(":[")[1]
        else:
            attributes = section[j]
        for attribute in attributes.split("],\n")[0].split(","):
            if attribute != "\n":
                attribute_names.append(attribute.strip())
        print("class_name: ", class_name)
        print(attribute_names)

         # loop untile find "data"
        j += 1
        data = []
        if "data" in section[j]:
            j += 1
        while "]" not in section[j]:
            if "[" in section[j]:
                for d in section[j].split('[')[1].split(','):
                    if d != "\n":
                        data.append(d.strip())
            else:
                for d in section[j].split(','):
                    if d != "\n":
                        data.append(d.strip())
            j += 1
        # '],' in section[j]:
        if "[" in section[j]:
            data_string = section[j].split('[')[1]
        else:
            data_string = section[j]
        for d in data_string.split(']')[0].split(','):
            if d != "\n":
                data.append(d.strip())
        print(data)
        data_types = [type(convert_type(element)) for element in data]
        print(data_types)
        print(data[0], type(data[0]))

        print((len(data) == len(attribute_names)), len(data) ,len(attribute_names))
        if len(data) != len(attribute_names):
            print(f"RAWX Section {i}:")
            for part in section:
                print(part)
            print("\n" + "="*50 + "\n")
        if len(data) == len(attribute_names):
            jsons.append((class_name, data, attribute_names))

    print("we got json:", len(jsons), jsons)
    return jsons

def convert_to_json_structure(data):
    """ Convert extracted data into structured JSON format """
    json_structure = []

    for class_name, values, attributes in data:
        class_dict = {
            "name": class_name.strip('"'),
            "stereotype": "TNP",  # Always "TNP"
            "attributes": [
                {"name": attr.strip('"'), "type": infer_type(val)}
                for attr, val in zip(attributes, values)
            ]
        }
        json_structure.append(class_dict)

    return json_structure       

def extract_json_after_rawx(file_path):
    with open(file_path, 'r', encoding = "utf-8") as file:
        raw_data = file.read()

    pattern = r'RAWX Data Table Format\s*"(\w+)"\s*:\s*({.*?})'
    matches = re.findall(pattern, raw_data, re.DOTALL)

    extracted_data = []

    for match in matches:
        try:
            json_object = json.loads(match[1])
            extracted_data.append(json_object)

        except json.JSONDecodeError:
            print("Error decoding JSON:", match)
    return extracted_data

file_path = "DataFormats.txt"
rawx_data_list = extract_rawx_sections(file_path)
formated_data = ea_formater(rawx_data_list)
json_format = convert_to_json_structure(formated_data)
print(json.dumps(json_format, indent=4))
file_path = "output.json"

# Write to a file with indentation for readability
with open(file_path, "w", encoding="utf-8") as json_file:
    json.dump(json_format, json_file, indent=4)
# for i, section in enumerate(rawx_data_list, 1):
#     print(f"RAWX Section {i}:")
#     for part in section:
#         print(part)
#     print("\n" + "="*50 + "\n")


# json_data_list = extract_json_after_rawx(file_path)

# for i, json_data in enumerate(json_data_list, 1):
#     print(f"RAWX JSON {i}:")
#     print(json.dumps(json_data, indent = 4))