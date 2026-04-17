with open('src/bioetl/application/composite/column_orderer.py', 'r') as f:
    content = f.read()

import_str = "from bioetl.application.composite.column_service import collect_explicit_group_columns\n"
if "from bioetl.application.composite.column_service" not in content:
    content = content.replace(
        "from bioetl.domain.value_objects.column_order import (",
        import_str + "from bioetl.domain.value_objects.column_order import ("
    )

with open('src/bioetl/application/composite/column_orderer.py', 'w') as f:
    f.write(content)
