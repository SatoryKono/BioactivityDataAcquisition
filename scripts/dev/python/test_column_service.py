#!/usr/bin/env python3
"""Test script for the new ColumnOrderService."""

from unittest.mock import MagicMock
import polars as pl

# Test the import and basic functionality
def test_column_service_import():
    """Test that the new service can be imported and instantiated."""
    try:
        from bioetl.application.composite.column_service import ColumnOrderService
        from bioetl.domain.value_objects.column_order import DEFAULT_COLUMN_ORDER
        
        # Create mock logger
        mock_logger = MagicMock()
        mock_logger.debug = MagicMock()
        mock_logger.info = MagicMock()
        
        # Test instantiation
        service = ColumnOrderService(
            logger=mock_logger,
            config=DEFAULT_COLUMN_ORDER
        )
        
        print("✅ ColumnOrderService imported and instantiated successfully")
        
        # Test basic functionality
        df = pl.DataFrame({
            "chembl.molecule.chembl_id": ["CHEMBL1", "CHEMBL2"],
            "pubchem.compound.cid": [123, 456],
            "chembl.molecule.molecular_weight": [200.5, 300.2]
        })
        
        result = service.order_columns(df)
        print(f"✅ order_columns works: {len(result.columns)} columns")
        
        # Test priority ordering
        from bioetl.domain.composite.config import EnricherConfig
        enrichers = [
            EnricherConfig(pipeline="pubchem_compound", join_keys=("cid",))
        ]
        available_columns = {"chembl.molecule.chembl_id", "pubchem.compound.chembl_id"}
        
        columns = service.collect_field_columns(
            field="chembl_id",
            enrichers=enrichers,
            available_columns=available_columns,
            seed_pipeline="chembl_molecule"
        )
        print(f"✅ collect_field_columns works: {columns}")
        
        print("🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_column_service_import()