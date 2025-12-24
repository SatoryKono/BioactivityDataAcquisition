"""Unified Cleanup Service.

Application Service для очистки данных Silver и Gold слоёв.
Единая точка входа для preview и actual cleanup операций.

Implements RULES.md §2.3 - Medallion Architecture cleanup invariants.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from bioetl.domain.types import CleanupPreview, CleanupResult, LayerPreview

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, StoragePort


class CleanupService:
    """Сервис унифицированной очистки данных.

    Предоставляет единую точку входа для:
    - Предпросмотра очистки (preview)
    - Выполнения очистки (execute)

    Соблюдает архитектурные инварианты Medallion:
    - Очистка только для REBUILD и BACKFILL операций
    - INCREMENTAL операции используют merge/upsert

    Example:
        >>> service = CleanupService(storage=storage, logger=logger)
        >>> preview = await service.preview("chembl.activity", "chembl.activity")
        >>> result = await service.execute("chembl.activity", "chembl.activity", dry_run=False)
    """

    def __init__(self, storage: StoragePort, logger: LoggerPort) -> None:
        """Инициализация сервиса очистки.

        Args:
            storage: Порт хранилища данных.
            logger: Порт логирования.
        """
        self._storage = storage
        self._logger = logger

    async def preview(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> CleanupPreview:
        """Предпросмотр операции очистки без фактического удаления.

        Args:
            silver_table: Имя таблицы Silver слоя.
            gold_table: Имя таблицы Gold слоя (опционально).

        Returns:
            CleanupPreview с информацией о файлах для очистки.
        """
        # StoragePort.preview_cleanup возвращает dict[str, Any]
        # Выполняем в executor для избежания блокировки event loop
        loop = asyncio.get_running_loop()
        preview_dict: dict[str, Any] = await loop.run_in_executor(
            None,
            lambda: self._storage.preview_cleanup(
                silver_table=silver_table,
                gold_table=gold_table,
            ),
        )

        # Преобразуем dict в типизированный CleanupPreview
        silver_info = preview_dict["silver"]
        silver_preview = LayerPreview(
            path=silver_info["path"],
            file_count=silver_info["file_count"],
            exists=silver_info["exists"],
        )

        gold_preview: LayerPreview | None = None
        if preview_dict.get("gold"):
            gold_info = preview_dict["gold"]
            gold_preview = LayerPreview(
                path=gold_info["path"],
                file_count=gold_info["file_count"],
                exists=gold_info["exists"],
            )

        return CleanupPreview(
            silver=silver_preview,
            gold=gold_preview,
            total_files=preview_dict["total_files"],
        )

    async def execute(
        self,
        silver_table: str,
        gold_table: str | None = None,
        *,
        dry_run: bool = False,
    ) -> CleanupResult:
        """Выполнение очистки Silver и Gold слоёв.

        Args:
            silver_table: Имя таблицы Silver слоя.
            gold_table: Имя таблицы Gold слоя (опционально).
            dry_run: Если True, только подсчитывает без удаления.

        Returns:
            CleanupResult с информацией об очищенных элементах.
        """
        # Очистка Silver слоя
        silver_cleared = await self._storage.clear_silver(
            silver_table, dry_run=dry_run
        )

        # Очистка Gold слоя (если указано)
        gold_cleared = 0
        if gold_table:
            gold_cleared = await self._storage.clear_gold(gold_table, dry_run=dry_run)

        total_cleared = silver_cleared + gold_cleared

        # Логирование результатов
        if dry_run:
            self._logger.info(
                "DRY RUN: Would clear storage",
                extra={
                    "silver_table": silver_table,
                    "gold_table": gold_table,
                    "silver_would_clear": silver_cleared,
                    "gold_would_clear": gold_cleared,
                },
            )
        elif total_cleared > 0:
            self._logger.info(
                "Cleared storage",
                extra={
                    "silver_table": silver_table,
                    "gold_table": gold_table,
                    "silver_cleared": silver_cleared,
                    "gold_cleared": gold_cleared,
                },
            )

        return CleanupResult(
            silver_cleared=silver_cleared,
            gold_cleared=gold_cleared,
            total_cleared=total_cleared,
            dry_run=dry_run,
        )
