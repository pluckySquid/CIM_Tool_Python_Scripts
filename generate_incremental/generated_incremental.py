import pandas as pd
import xml.etree.ElementTree as ET

# --- Namespaces ---
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
CIM_NS = "http://iec.ch/TC57/2006/CIM-schema-cim10#"
ETX_NS = "http://www.ercot.com/CIM11R0/2008/2.0/extension#"
ns = {
    'rdf': RDF_NS,
    'cim': CIM_NS,
    'etx': ETX_NS
}

cim_equipment_classes = {
    "ACDCConverter",
    "ACLineSegment",
    "Breaker",
    "BusbarSection",
    "Conductor",
    "CsConverter",
    "CurrentTransformer",
    "DCLineSegment",
    "Disconnector",
    "EnergyConsumer",
    "EnergySource",
    "ExternalNetworkInjection",
    "Fuse",
    "GeneratingUnit",
    "GroundDisconnector",
    "HydroGeneratingUnit",
    "LinearShuntCompensator",
    "LoadBreakSwitch",
    "MeteringEquipment",
    "PotentialTransformer",
    "PowerTransformer",
    "PowerTransformerEnd",
    "ProtectionEquipment",
    "Recloser",
    "Sensor",
    "SeriesCompensator",
    "ShuntCompensator",
    "SolarGeneratingUnit",
    "StaticVarCompensator",
    "SynchronousMachine",
    "SurgeArrester",
    "Switch",  # abstract, but base for all switch types
    "ThermalGeneratingUnit",
    "VsConverter",
    "WindGeneratingUnit",
    #Yunshu added
    "PowerSystemResource",
    "Operatorship",
    "PermissionArea",
    "SettlementLoadZone",
    "Region",
    "VoltageLevel"
    "HostControlArea",
    "Ownership"
}

ref_not_include = {
    "Substation.Region"
}

ET.register_namespace('rdf', RDF_NS)
ET.register_namespace('cim', CIM_NS)
ET.register_namespace('etx', ETX_NS)

# --- Load incremental substation names from Excel ---
df = pd.read_excel('TNMP_SUBSTATIONS.xlsx')
incremental_substation_names = df.get("ERCOT SUB NAME").dropna().tolist()
incremental_substation_names_set = set(incremental_substation_names)
print("Total substations to match:", len(incremental_substation_names_set))

# --- Parse the original CIM XML file ---
example_file = r"C:\Users\ywang2\work\CIM\NMMS_Model_CIM_Mar_ML1_1_03112025.xml"
tree = ET.parse(example_file)
root = tree.getroot()

# --- Extract matching Substations ---
substations = {}
found_substation_names_set = set()

for el in root.findall("cim:Substation", ns):
    rdf_id = el.attrib.get(f"{{{RDF_NS}}}ID")
    name_el = el.find("cim:IdentifiedObject.name", ns)
    name = name_el.text.strip() if name_el is not None and name_el.text else None
    refs = []
    for child in el:
        resource = child.attrib.get(f"{{{RDF_NS}}}resource")
        tag = child.tag.split("}", 1)[1]
        if resource and resource.startswith("#"):
            if tag in ref_not_include:
                continue
            ref_id = resource[1:]  # remove leading "#"    refs = refs_el if refs_el is not None and refs_el.text else []
            refs.append(ref_id)

    if name:
        substations[name] = (rdf_id, el, refs)
        found_substation_names_set.add(name)
    #print(name, refs)

missing = incremental_substation_names_set - found_substation_names_set
print(f"Total substations: {len(found_substation_names_set)}")
print(f"Missing substations: {missing}")

# --- Collect matched Substation elements and IDs ---
incremental_substation_els = []
incremental_substation_ids = set()
incremental_substation_refs = set()

for name in incremental_substation_names_set:
    if name in substations:
        rdf_id, el, refs = substations[name]
        incremental_substation_els.append(el)
        incremental_substation_ids.add(rdf_id)
        for ref in refs:
            incremental_substation_refs.add(ref)
print("total references in the substation:", len(incremental_substation_refs))

# --- Find VoltageLevels that reference these substations ---
incremental_voltagelevel_els = []
incremental_voltagelevel_ids=set()
for el in root.findall("cim:VoltageLevel", ns):
    rdf_id = el.attrib.get(f"{{{RDF_NS}}}ID")
    for child in el:
        resource = child.attrib.get(f"{{{RDF_NS}}}resource")
        if resource and resource.startswith("#"):
            ref_id = resource[1:]  # remove leading "#"
            if ref_id in incremental_substation_ids or ref_id in incremental_substation_refs:
                incremental_voltagelevel_els.append(el)
                incremental_voltagelevel_ids.add(rdf_id)
                break
print("length of incremental_voltagelevel_els:", len(incremental_voltagelevel_els))


# trying to add all the missing ACLinesegments
incremental_ACLineSegment_els = []
incremental_ACLineSegment_ids=set()
for el in root.findall("cim:ACLineSegment", ns):
    rdf_id = el.attrib.get(f"{{{RDF_NS}}}ID")
    for child in el:
        resource = child.attrib.get(f"{{{RDF_NS}}}resource")
        if resource and resource.startswith("#"):
            ref_id = resource[1:]  # remove leading "#"
            if ref_id in incremental_substation_ids or ref_id in incremental_substation_refs:
                incremental_ACLineSegment_els.append(el)
                incremental_ACLineSegment_ids.add(rdf_id)
                break
print("length of incremental_ACLineSegment_els:", len(incremental_ACLineSegment_els))


# this can find all elements who referenced substation's references
incremental_equipments_els = []
incremental_equipments_ids = set()
for el in root:
    rdf_id = el.attrib.get(f"{{{RDF_NS}}}ID")
    if rdf_id in incremental_substation_refs:
        incremental_equipments_els.append(el)
        incremental_equipments_ids.add(rdf_id)
        continue
    # if el.tag.split('}', 1)[1] not in cim_equipment_classes:
    #     #print("not in", el.tag)
    #     continue
    for child in el:
        resource = child.attrib.get(f"{{{RDF_NS}}}resource")
        if resource and resource.startswith("#"):
            ref_id = resource[1:]  # remove leading "#"
            if ref_id in incremental_substation_ids or ref_id in incremental_voltagelevel_ids:
                incremental_equipments_els.append(el)
                incremental_equipments_ids.add(rdf_id)
                break

# get all the terminals that ACLiensegments link to
incremental_Terminal_els=[]
incremental_Terminal_ids = set()
for el in root.findall("cim:Terminal", ns):
    rdf_id = el.attrib.get(f"{{{RDF_NS}}}ID")
    for child in el:
        resource = child.attrib.get(f"{{{RDF_NS}}}resource")
        if resource and resource.startswith("#"):
            ref_id = resource[1:]  # remove leading "#"
            if ref_id in incremental_substation_ids or ref_id in incremental_ACLineSegment_ids or ref_id in incremental_equipments_ids:
                incremental_Terminal_els.append(el)
                incremental_Terminal_ids.add(rdf_id)
                break
print("length of incremental_Terminal_els:", len(incremental_Terminal_els))

# get all the terminals that ACLiensegments link to
incremental_Disconnector_els=[]
for el in root.findall("cim:Disconnector", ns):
    rdf_id = el.attrib.get(f"{{{RDF_NS}}}ID")
    for child in el:
        resource = child.attrib.get(f"{{{RDF_NS}}}resource")
        if resource and resource.startswith("#"):
            ref_id = resource[1:]  # remove leading "#"
            if ref_id in incremental_Terminal_ids:
                incremental_Disconnector_els.append(el)
                break
print("length of incremental_Terminal_els:", len(incremental_Disconnector_els))

# this can find who referenced substation's reference
# incremental_equipments_els = []
# for el in root:
#     for child in el:
#         resource = child.attrib.get(f"{{{RDF_NS}}}resource")
#         if resource and resource.startswith("#"):
#             ref_id = resource[1:]  # remove leading "#"
#             if ref_id in ref_id in incremental_equipments_els:
#                 incremental_equipments_els.append(el)
#                 break

# --- Build output RDF tree ---
rdf_root = ET.Element(f"{{{RDF_NS}}}RDF", {
    f"xmlns:rdf": RDF_NS,
    f"xmlns:cim": CIM_NS,
    f"xmlns:etx": ETX_NS
})
rdf_root.text = "\n"

# Append matched substations and voltage levels
# for el in incremental_substation_els + incremental_voltagelevel_els:
#     rdf_root.append(el)
for el in list(set(incremental_substation_els + incremental_voltagelevel_els+ incremental_equipments_els + incremental_ACLineSegment_els + incremental_Terminal_els + incremental_Disconnector_els)):
    rdf_root.append(el)

# --- Write output with short_empty_elements=False ---
output_file = "output_incremental.xml"
ET.ElementTree(rdf_root).write(
    output_file,
    encoding="utf-8",
    xml_declaration=True,
    short_empty_elements=False
)

print(f"✅ Output written to {output_file}")
print(f"Substations written: {len(incremental_substation_els)}")
# print(f"VoltageLevels written: {len(incremental_voltagelevel_els)}")
print(f"equioments written: {len(incremental_equipments_els)}")