with open('src/bioetl/application/composite/column_orderer.py', 'r') as f:
    content = f.read()

# Add the import correctly
import_str = "from bioetl.application.composite.column_service import collect_explicit_group_columns\n"
if "from bioetl.application.composite.column_service" not in content:
    content = content.replace(
        "from bioetl.domain.config.column_order_config import ColumnGroupConfig, ColumnOrderConfig\n",
        "from bioetl.domain.config.column_order_config import ColumnGroupConfig, ColumnOrderConfig\n" + import_str
    )

with open('src/bioetl/application/composite/column_orderer.py', 'w') as f:
    f.write(content)
