from lxml import etree
from copy import deepcopy
from collections import deque
import xml.etree.ElementTree as ET
from io import BytesIO

delete_file  = "delete_thurber_ranger_incremental.xml"
example_file = r"C:\Users\ywang2\work\CIM\NMMS_Model_CIM_Mar_ML1_1_03112025.xml"
output_file  = "output.xml"

RDF_NS   = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

safe_parser = etree.XMLParser(load_dtd=False, no_network=True, resolve_entities=False)


def get_id(val):
    return val[1:] if val and val.startswith("#") else None


# — 1) Load delete file —
with open(delete_file, "rb") as f:
    delete_tree = etree.parse(f, parser=safe_parser)
delete_root = delete_tree.getroot()

# — 2) Collect existing IDs & all resource references —
existing_ids   = set()
referenced_ids = set()

for el in delete_root.iter():
    rid = el.get(f"{{{RDF_NS}}}ID")
    if rid:
        existing_ids.add(rid)
    for attr, val in el.attrib.items():
        if attr.endswith("resource"):
            ref = get_id(val)
            if ref:
                referenced_ids.add(ref)

missing_ids = referenced_ids - existing_ids
queue = deque(sorted(missing_ids))

print(f"📌 Start: {len(existing_ids)} defined, {len(referenced_ids)} referenced")
print(f"❓ Directly missing from delete file: {len(missing_ids)}")

initial_missing_ids = set(queue)

# — 3) Load example file & build ID→element map —
with open(example_file, "rb") as f:
    example_tree = etree.parse(f, parser=safe_parser)
example_root = example_tree.getroot()

example_dict = {
    el.get(f"{{{RDF_NS}}}ID"): el
    for el in example_root
    if el.get(f"{{{RDF_NS}}}ID") is not None
}

# — 4) BFS injection of all missing + indirect —
injected = set()
not_found = set()
level = 0

while queue:
    level_size = len(queue)
    level_injected = 0
    print(f"\n🌊 BFS level {level}: {level_size} IDs in queue")

    for _ in range(level_size):
        rid = queue.popleft()
        if rid in existing_ids or rid in injected or rid in not_found:
            continue

        src = example_dict.get(rid)
        if src is None:
            not_found.add(rid)
            continue

        el_copy = deepcopy(src)
        delete_root.append(el_copy)
        injected.add(rid)
        existing_ids.add(rid)
        level_injected += 1

        # queue up any new references found in the injected element
        for node in el_copy.iter():
            for attr_name, attr_val in node.attrib.items():
                if attr_name.endswith("resource"):
                    ref2 = get_id(attr_val)
                    if ref2 and ref2 not in existing_ids and ref2 not in injected and ref2 not in not_found:
                        queue.append(ref2)

    print(f"✅ Injected in level {level}: {level_injected}")
    level += 1

# — 5) Final reporting —
print(f"\n📦 FINAL SUMMARY")
print(f"Total injected (all levels): {len(injected)}")
print(f"Total missing (not in example.xml): {len(not_found)}")

if not_found:
    print("❌ Unresolved references:")
    for rid in sorted(not_found)[:20]:
        print("   -", rid)
    if len(not_found) > 20:
        print(f"   ... ({len(not_found) - 20} more)")
else:
    print("✅ All references resolved")

unresolved_direct = initial_missing_ids - injected
reachable_missing = unresolved_direct & not_found
print(f"\n📍 Direct references never injected: {len(unresolved_direct)}")
print(f"🔗 Of those, still unresolved in example.xml: {len(reachable_missing)}")

# — 6) Preserve only delete-file namespaces at root —
merged_nsmap = {}
for prefix, uri in delete_root.nsmap.items():
    if prefix:
        merged_nsmap[prefix] = uri

new_root = etree.Element(delete_root.tag, nsmap=merged_nsmap)
for child in delete_root:
    new_root.append(child)
delete_tree._setroot(new_root)

# clean up any stray inline xmlns:
etree.cleanup_namespaces(delete_tree, top_nsmap=merged_nsmap)

# — 7) Emit to bytes with lxml (correct namespaces, indentation + declaration) —
delete_xml_bytes = etree.tostring(
    delete_tree,
    encoding="utf-8",
    xml_declaration=True,
    pretty_print=True
)

example_xml_bytes = etree.tostring(
    example_tree,
    encoding="utf-8",
    xml_declaration=True,
    pretty_print=True
)
delete_xml_out = delete_xml_bytes.decode('utf-8')
# example_xml_out = example_xml_bytes.decode('utf-8')

# — 8) Extract and register namespaces from that text string —
def extract_namespaces_from_string(xml_string, ns_map):
    it = ET.iterparse(BytesIO(xml_string.encode('utf-8')), events=['start-ns'])
    #ns_map = {}
    for _, (prefix, uri) in it:
        if prefix and prefix not in ns_map:
            ns_map[prefix] = uri
            ET.register_namespace(prefix, uri)
    return ns_map

ns_map = {}
extract_namespaces_from_string(delete_xml_out, ns_map)
# extract_namespaces_from_string(example_xml_out, ns_map)
print(ns_map)

# — 9) Parse with stdlib ElementTree and write with no self-closing tags —
et_root = ET.fromstring(delete_xml_out)
et_tree = ET.ElementTree(et_root)
et_tree.write(
    output_file,
    encoding="utf-8",
    xml_declaration=True,
    short_empty_elements=False
)

print(f"\n💾 Merged XML written to: {output_file}")