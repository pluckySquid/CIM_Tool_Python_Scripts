import pandas as pd
import xml.etree.ElementTree as ET
from collections import deque, defaultdict

# --- Namespaces ---
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
CIM_NS = "http://iec.ch/TC57/2006/CIM-schema-cim10#"
ETX_NS = "http://www.ercot.com/CIM11R0/2008/2.0/extension#"
ns = {'rdf': RDF_NS, 'cim': CIM_NS, 'etx': ETX_NS}

# --- Register namespaces for output ---
ET.register_namespace('rdf', RDF_NS)
ET.register_namespace('cim', CIM_NS)
ET.register_namespace('etx', ETX_NS)

# --- Load TNMP substations from Excel ---
df = pd.read_excel('TNMP_SUBSTATIONS.xlsx')
#tnmp_names = df['ERCOT SUB NAME'].dropna().astype(str).tolist()

coast_df = df[df['ERCOT LOCATION'] == 'COAST']
tnmp_names = coast_df['ERCOT SUB NAME'].dropna().astype(str).tolist()

#tnmp_name_set = {"ALVIN"}#set(tnmp_names)
tnmp_name_set = set(tnmp_names)
print(f"Loaded {len(tnmp_name_set)} TNMP substation names.")

# --- Parse the CIM XML file ---
tree = ET.parse(r"C:/Users/ywang2/work/CIM/NMMS_Model_CIM_Mar_ML1_1_03112025.xml")
root = tree.getroot()

# --- Build RDF ID map and reverse reference map ---
rdf_id_map = {}
reverse_ref_map = defaultdict(set)
for el in root:
    rid = el.attrib.get(f"{{{RDF_NS}}}ID")
    if rid:
        rdf_id_map[rid] = el
    for child in el:
        res = child.attrib.get(f"{{{RDF_NS}}}resource")
        if res and res.startswith('#'):
            reverse_ref_map[res[1:]].add(rid)

# --- Identify all substations and map IDs to names ---
all_sub_ids = set()
sub_id_to_name = {}
for sub in root.findall('cim:Substation', ns):
    rid = sub.attrib.get(f"{{{RDF_NS}}}ID")
    name_el = sub.find('cim:IdentifiedObject.name', ns)
    name = name_el.text.strip() if name_el is not None and name_el.text else None
    if rid and name:
        all_sub_ids.add(rid)
        sub_id_to_name[rid] = name
print(f"Found {len(all_sub_ids)} total substations in the model.")

# --- Determine which substations are in TNMP ---
tnmp_sub_ids = {sid for sid, name in sub_id_to_name.items() if name in tnmp_name_set}
print(f"TNMP substations count: {len(tnmp_sub_ids)}")

# --- Multi-source BFS: label origins for each node ---
origins = defaultdict(set)   # node_id -> set of source substation IDs
queue = deque()

# Seed BFS with every substation as its own origin
for sid in all_sub_ids:
    origins[sid].add(sid)
    queue.append((sid, sid))

while queue:
    node_id, origin = queue.popleft()
    el = rdf_id_map.get(node_id)
    if el is None:
        continue
    # forward neighbors
    neighbors = []
    for child in el:
        res = child.attrib.get(f"{{{RDF_NS}}}resource")
        if res and res.startswith('#'):
            neighbors.append(res[1:])
    # reverse neighbors
    neighbors.extend(reverse_ref_map.get(node_id, []))

    for nbr in neighbors:
        if origin in origins[nbr]:
            continue
        origins[nbr].add(origin)
        # enqueue neighbor only if it remains single-origin
        if len(origins[nbr]) == 1:
            queue.append((nbr, origin))

# --- Collect elements for TNMP substations ---
final_ids = set()
for rid, origin_set in origins.items():
    # unique to a TNMP substation
    if len(origin_set) == 1 and next(iter(origin_set)) in tnmp_sub_ids:
        final_ids.add(rid)
    # boundary elements that touch any TNMP substation
    elif len(origin_set) > 1 and origin_set & tnmp_sub_ids:
        final_ids.add(rid)

print(f"Total elements for TNMP output: {len(final_ids)}")

# --- Build output RDF tree ---
rdf_root = ET.Element(
    f"{{{RDF_NS}}}RDF",
    {f"xmlns:rdf": RDF_NS, f"xmlns:cim": CIM_NS, f"xmlns:etx": ETX_NS}
)
rdf_root.text = '\n'
for rid in final_ids:
    el = rdf_id_map.get(rid)
    if el is not None:
        rdf_root.append(el)

# --- Write reduced XML module ---
output_file = 'tnmp_reduced_module_bfs.xml'
ET.ElementTree(rdf_root).write(
    output_file,
    encoding='utf-8',
    xml_declaration=True,
    short_empty_elements=False
)
print(f"✅ Wrote '{output_file}' with {len(final_ids)} elements.")
