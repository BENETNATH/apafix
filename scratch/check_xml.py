from lxml import etree
import os

file_path = 'Phnotypageduneligned_2025092611077747_v1.xml'
with open(file_path, 'rb') as f:
    content = f.read()

root = etree.fromstring(content)
print(f"Tag: {root.tag}")
print(f"Attrib: {root.attrib}")
print(f"NSMap: {root.nsmap}")

# Check processing instructions
tree = etree.ElementTree(root)
for pi in root.xpath('//processing-instruction()'):
    print(f"PI: {pi.target} -> {pi.text}")
