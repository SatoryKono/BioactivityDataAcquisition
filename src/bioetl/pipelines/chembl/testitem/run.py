from typing import Any

import pandas as pd

from bioetl.pipelines.chembl.common.base import ChemblCommonPipeline


class ChemblTestitemPipeline(ChemblCommonPipeline):
    """
    TestItem pipeline: извлекает данные молекул из ChEMBL /molecule endpoint.
    Трансформирует в формат testitem согласно схеме.
    """

    # Колонки для выходного датасета
    OUTPUT_COLUMNS = [
        "molecule_chembl_id",
        "molecule_type",
        "pref_name",
        "max_phase",
    ]

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Трансформация данных molecule в testitem формат.
        Выбирает нужные поля и приводит типы.
        """
        # Выбираем только нужные колонки
        available_cols = [c for c in self.OUTPUT_COLUMNS if c in df.columns]
        result = df[available_cols].copy()

        # Приводим max_phase к int, заменяя None на pd.NA
        if "max_phase" in result.columns:
            result["max_phase"] = pd.to_numeric(
                result["max_phase"], errors="coerce"
            ).astype("Int64")

        return result

