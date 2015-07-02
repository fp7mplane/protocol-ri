#!/usr/bin/env python3

import json

with open("../mplane/registry.json", mode="r") as rf:
    rb = json.load(rf)

print("| Name | Primitive | Desciption                                  |")
print("| ---- | --------- | ------------------------------------------- |")

for elem in rb['elements']:
    print("| " + elem['name'] + " | " + elem['prim'] + " | " + elem['desc'] + " |")
