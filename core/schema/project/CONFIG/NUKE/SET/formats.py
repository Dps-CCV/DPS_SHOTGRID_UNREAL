import nuke

new_formats = [
    '3200 1800 LCC_format',
]

for f in new_formats:
    nuke.addFormat(f)