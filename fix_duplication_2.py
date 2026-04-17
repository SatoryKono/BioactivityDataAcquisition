with open('src/bioetl/application/composite/column_orderer.py', 'r') as f:
    content = f.read()

# Fix W293 and move import to top
import re

# Remove the import we just added in the middle
content = content.replace("from bioetl.application.composite.column_service import collect_explicit_group_columns\n", "")

# Add it at the top with other bioetl imports
content = re.sub(
    r"from bioetl\.domain\.config\.column_order_config import ColumnGroupConfig, ColumnOrderConfig",
    "from bioetl.domain.config.column_order_config import ColumnGroupConfig, ColumnOrderConfig\nfrom bioetl.application.composite.column_service import collect_explicit_group_columns",
    content
)

# Fix whitespace
content = content.replace("    \n    .. deprecated::", "\n    .. deprecated::")

with open('src/bioetl/application/composite/column_orderer.py', 'w') as f:
    f.write(content)
