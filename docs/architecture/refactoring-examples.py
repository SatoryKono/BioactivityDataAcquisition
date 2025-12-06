"""
Примеры рефакторинга ключевых компонентов BioETL
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Type

import numpy as np
import pandas as pd
from dependency_injector import containers, providers

# ============================================================================
# ПРИМЕР 1: Рефакторинг системы нормализации
# ============================================================================

# --- До рефакторинга (текущий код) ---
class OldNormalizer:
    """Текущая реализация с множеством if-else и смешанной логикой"""
    
    def normalize_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        for field_cfg in self._config.fields:
            name = field_cfg["name"]
            dtype = field_cfg.get("data_type")
            
            if name not in df.columns:
                continue
                
            # Огромная простыня if-else логики
            mode = "default"
            if name in CASE_SENSITIVE_FIELDS:
                mode = "sensitive"
            elif is_id_field(name):
                mode = "id"
                
            if name in CUSTOM_FIELD_NORMALIZERS:
                base_normalizer = CUSTOM_FIELD_NORMALIZERS[name]
            else:
                # Еще больше if-else...
                pass
                
            # Row-by-row обработка - МЕДЛЕННО!
            df[name] = df[name].apply(lambda x: self.normalize_value(x, mode))
        
        return df


# --- После рефакторинга ---

class NormalizationType(Enum):
    """Типы нормализации"""
    IDENTIFIER = "identifier"
    CHEMICAL = "chemical"
    NUMERIC = "numeric"
    TEXT = "text"
    NESTED = "nested"


@dataclass
class FieldConfig:
    """Строго типизированная конфигурация поля"""
    name: str
    data_type: str
    normalization_type: NormalizationType
    case_sensitive: bool = False
    precision: Optional[int] = None
    validators: List[str] = None


class NormalizationStrategy(ABC):
    """Абстрактная стратегия нормализации"""
    
    @abstractmethod
    def normalize(self, value: Any) -> Any:
        """Нормализует одно значение"""
        pass
    
    @abstractmethod
    def normalize_series(self, series: pd.Series) -> pd.Series:
        """Векторизованная нормализация для pandas Series"""
        pass


class IdentifierNormalizationStrategy(NormalizationStrategy):
    """Стратегия для научных идентификаторов"""
    
    def __init__(self, identifier_type: str):
        self.identifier_type = identifier_type
        
    def normalize(self, value: Any) -> Any:
        if pd.isna(value) or value is None:
            return None
            
        str_value = str(value).strip().upper()
        
        # Специфичная логика для разных типов ID
        if self.identifier_type == "chembl":
            if str_value.isdigit():
                str_value = f"CHEMBL{str_value}"
            if not str_value.startswith("CHEMBL"):
                raise ValueError(f"Invalid ChEMBL ID: {value}")
                
        elif self.identifier_type == "doi":
            str_value = str_value.lower()
            # Remove common prefixes
            for prefix in ["doi:", "http://dx.doi.org/"]:
                if str_value.startswith(prefix):
                    str_value = str_value[len(prefix):]
                    
        return str_value
    
    def normalize_series(self, series: pd.Series) -> pd.Series:
        """Векторизованная версия для производительности"""
        # Используем pandas строковые методы для векторизации
        result = series.str.strip().str.upper()
        
        if self.identifier_type == "chembl":
            # Векторизованное добавление префикса
            is_numeric = result.str.isdigit()
            result[is_numeric] = "CHEMBL" + result[is_numeric]
            
        elif self.identifier_type == "doi":
            result = result.str.lower()
            for prefix in ["doi:", "http://dx.doi.org/"]:
                mask = result.str.startswith(prefix)
                result[mask] = result[mask].str[len(prefix):]
                
        return result


class NumericNormalizationStrategy(NormalizationStrategy):
    """Стратегия для числовых значений"""
    
    def __init__(self, precision: int = 3):
        self.precision = precision
        
    def normalize(self, value: Any) -> Any:
        if pd.isna(value) or value is None:
            return None
        
        if isinstance(value, (int, float)):
            return round(float(value), self.precision)
            
        return value
    
    def normalize_series(self, series: pd.Series) -> pd.Series:
        """Векторизованное округление"""
        return series.round(self.precision)


class ChemicalStructureNormalizationStrategy(NormalizationStrategy):
    """Стратегия для химических структур (SMILES, InChI)"""
    
    def normalize(self, value: Any) -> Any:
        if pd.isna(value) or value is None:
            return None
        
        # Сохраняем регистр для химических структур
        return str(value).strip()
    
    def normalize_series(self, series: pd.Series) -> pd.Series:
        """Векторизованная обработка с сохранением регистра"""
        return series.str.strip()


class NormalizerFactory:
    """Фабрика для создания нормализаторов"""
    
    def __init__(self):
        self._strategies: Dict[NormalizationType, Type[NormalizationStrategy]] = {
            NormalizationType.IDENTIFIER: IdentifierNormalizationStrategy,
            NormalizationType.NUMERIC: NumericNormalizationStrategy,
            NormalizationType.CHEMICAL: ChemicalStructureNormalizationStrategy,
        }
        
    def create_normalizer(self, field_config: FieldConfig) -> NormalizationStrategy:
        """Создает подходящий нормализатор на основе конфигурации"""
        strategy_class = self._strategies.get(field_config.normalization_type)
        
        if not strategy_class:
            raise ValueError(f"Unknown normalization type: {field_config.normalization_type}")
            
        # Создаем с параметрами из конфигурации
        if field_config.normalization_type == NormalizationType.NUMERIC:
            return strategy_class(precision=field_config.precision or 3)
        elif field_config.normalization_type == NormalizationType.IDENTIFIER:
            # Извлекаем тип ID из имени поля
            id_type = self._extract_id_type(field_config.name)
            return strategy_class(identifier_type=id_type)
        else:
            return strategy_class()
            
    def _extract_id_type(self, field_name: str) -> str:
        """Определяет тип идентификатора по имени поля"""
        if "chembl" in field_name.lower():
            return "chembl"
        elif "doi" in field_name.lower():
            return "doi"
        elif "pubmed" in field_name.lower():
            return "pubmed"
        else:
            return "generic"


class OptimizedNormalizer:
    """Оптимизированный нормализатор с векторизацией"""
    
    def __init__(self, factory: NormalizerFactory):
        self.factory = factory
        
    def normalize_dataframe(self, df: pd.DataFrame, fields: List[FieldConfig]) -> pd.DataFrame:
        """Нормализует DataFrame используя векторизованные операции"""
        df = df.copy()
        
        for field_config in fields:
            if field_config.name not in df.columns:
                continue
                
            # Создаем стратегию для поля
            strategy = self.factory.create_normalizer(field_config)
            
            # Используем векторизованную нормализацию
            df[field_config.name] = strategy.normalize_series(df[field_config.name])
            
        return df


# ============================================================================
# ПРИМЕР 2: Dependency Injection Container
# ============================================================================

class Container(containers.DeclarativeContainer):
    """DI Container для управления зависимостями"""
    
    # Configuration
    config = providers.Configuration()
    
    # Infrastructure services
    chembl_client = providers.Singleton(
        "AsyncChemblClient",
        api_key=config.chembl.api_key,
        base_url=config.chembl.base_url,
    )
    
    cache_service = providers.Singleton(
        "CacheService",
        redis_url=config.cache.redis_url,
        ttl=config.cache.ttl,
    )
    
    # Domain services
    normalizer_factory = providers.Singleton(NormalizerFactory)
    
    normalizer = providers.Factory(
        OptimizedNormalizer,
        factory=normalizer_factory,
    )
    
    hash_service = providers.Singleton(
        "HashService",
        algorithm=config.hashing.algorithm,
    )
    
    validation_service = providers.Singleton(
        "ValidationService",
        schema_registry=providers.Singleton("SchemaRegistry"),
    )
    
    # Application services
    data_extractor = providers.Factory(
        "DataExtractor",
        client=chembl_client,
        cache=cache_service,
    )
    
    data_transformer = providers.Factory(
        "DataTransformer",
        normalizer=normalizer,
        hash_service=hash_service,
    )
    
    data_validator = providers.Factory(
        "DataValidator",
        validation_service=validation_service,
    )
    
    data_writer = providers.Factory(
        "DataWriter",
        output_path=config.output.path,
    )
    
    # Pipeline orchestrator
    pipeline_orchestrator = providers.Factory(
        "PipelineOrchestrator",
        extractor=data_extractor,
        transformer=data_transformer,
        validator=data_validator,
        writer=data_writer,
    )


# ============================================================================
# ПРИМЕР 3: Параллельная обработка батчей
# ============================================================================

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Iterator

logger = logging.getLogger(__name__)


class ParallelBatchProcessor:
    """Параллельная обработка батчей данных"""
    
    def __init__(self, n_workers: int = 4):
        self.n_workers = n_workers
        
    def process_batches(
        self,
        data_source: Iterator[pd.DataFrame],
        processor_fn: callable,
        batch_size: int = 10000
    ) -> pd.DataFrame:
        """
        Обрабатывает батчи данных параллельно
        
        Args:
            data_source: Итератор, возвращающий батчи DataFrame
            processor_fn: Функция обработки одного батча
            batch_size: Размер батча
            
        Returns:
            Объединенный результат всех батчей
        """
        results = []
        
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            # Запускаем обработку батчей
            future_to_batch = {
                executor.submit(processor_fn, batch): idx
                for idx, batch in enumerate(data_source)
            }
            
            # Собираем результаты по мере готовности
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                
                try:
                    result = future.result()
                    results.append((batch_idx, result))
                    logger.info(f"Batch {batch_idx} processed successfully")
                    
                except Exception as exc:
                    logger.error(f"Batch {batch_idx} failed: {exc}")
                    raise
                    
        # Сортируем по индексу для сохранения порядка
        results.sort(key=lambda x: x[0])
        
        # Объединяем результаты
        return pd.concat([r[1] for r in results], ignore_index=True)


class StreamingDataProcessor:
    """Потоковая обработка больших файлов"""
    
    def __init__(self, chunk_size: int = 10000):
        self.chunk_size = chunk_size
        
    def process_file_streaming(
        self,
        file_path: str,
        processor_fn: callable,
        output_path: str
    ):
        """
        Обрабатывает большой файл по частям без загрузки в память
        
        Args:
            file_path: Путь к входному файлу
            processor_fn: Функция обработки чанка
            output_path: Путь к выходному файлу
        """
        first_chunk = True
        
        # Читаем и обрабатываем файл чанками
        for chunk_df in pd.read_csv(file_path, chunksize=self.chunk_size):
            # Обрабатываем чанк
            processed_chunk = processor_fn(chunk_df)
            
            # Записываем результат
            mode = 'w' if first_chunk else 'a'
            header = first_chunk
            
            processed_chunk.to_csv(
                output_path,
                mode=mode,
                header=header,
                index=False
            )
            
            first_chunk = False
            
            logger.info(f"Processed chunk with {len(chunk_df)} rows")


# ============================================================================
# ПРИМЕР 4: Композиция вместо наследования
# ============================================================================

class PipelineOrchestrator:
    """Оркестратор пайплайна через композицию"""
    
    def __init__(
        self,
        extractor: "DataExtractor",
        transformer: "DataTransformer",
        validator: "DataValidator",
        writer: "DataWriter",
        monitor: Optional["PipelineMonitor"] = None
    ):
        self.extractor = extractor
        self.transformer = transformer
        self.validator = validator
        self.writer = writer
        self.monitor = monitor
        
    def run(
        self,
        config: Dict[str, Any],
        output_path: str,
        streaming: bool = False
    ) -> Dict[str, Any]:
        """
        Запускает пайплайн обработки данных
        
        Args:
            config: Конфигурация пайплайна
            output_path: Путь для сохранения результатов
            streaming: Использовать потоковую обработку
            
        Returns:
            Результаты выполнения пайплайна
        """
        if self.monitor:
            self.monitor.start_pipeline(config["entity_name"])
            
        try:
            # 1. Extract
            if self.monitor:
                self.monitor.start_stage("extract")
                
            if streaming:
                data_iterator = self.extractor.extract_streaming(config)
            else:
                data = self.extractor.extract(config)
                
            # 2. Transform
            if self.monitor:
                self.monitor.start_stage("transform")
                
            if streaming:
                for chunk in data_iterator:
                    transformed = self.transformer.transform(chunk)
                    validated = self.validator.validate(transformed)
                    self.writer.write_chunk(validated, output_path)
            else:
                transformed = self.transformer.transform(data)
                
                # 3. Validate
                if self.monitor:
                    self.monitor.start_stage("validate")
                    
                validated = self.validator.validate(transformed)
                
                # 4. Write
                if self.monitor:
                    self.monitor.start_stage("write")
                    
                result = self.writer.write(validated, output_path)
                
            if self.monitor:
                metrics = self.monitor.end_pipeline()
                
            return {
                "status": "success",
                "metrics": metrics if self.monitor else None,
                "output_path": output_path
            }
            
        except Exception as e:
            if self.monitor:
                self.monitor.record_error(str(e))
            raise


# ============================================================================
# ПРИМЕР 5: Векторизованные операции для производительности
# ============================================================================

class VectorizedOperations:
    """Примеры векторизованных операций вместо apply()"""
    
    @staticmethod
    def normalize_ids_vectorized(series: pd.Series, id_type: str) -> pd.Series:
        """Векторизованная нормализация идентификаторов"""
        # Вместо apply() используем векторные операции
        
        if id_type == "chembl":
            # Векторное преобразование строк
            result = series.str.strip().str.upper()
            
            # Векторная проверка и модификация
            is_numeric = result.str.match(r'^\d+$', na=False)
            result[is_numeric] = 'CHEMBL' + result[is_numeric]
            
            return result
            
        elif id_type == "doi":
            # Векторные строковые операции
            result = series.str.strip().str.lower()
            
            # Удаление префиксов векторно
            result = result.str.replace(r'^doi:', '', regex=True)
            result = result.str.replace(r'^https?://dx\.doi\.org/', '', regex=True)
            
            return result
            
    @staticmethod
    def round_numbers_vectorized(series: pd.Series, decimals: int = 3) -> pd.Series:
        """Векторизованное округление чисел"""
        # NumPy операции намного быстрее чем apply()
        return pd.Series(
            np.where(
                pd.isna(series),
                np.nan,
                np.round(series.values, decimals)
            ),
            index=series.index
        )
        
    @staticmethod
    def clean_text_vectorized(series: pd.Series) -> pd.Series:
        """Векторизованная очистка текста"""
        # Цепочка векторных операций
        return (
            series
            .str.strip()
            .str.lower()
            .str.replace(r'\s+', ' ', regex=True)  # Множественные пробелы
            .str.replace(r'[^\w\s-]', '', regex=True)  # Специальные символы
        )


# ============================================================================
# Использование рефакторированного кода
# ============================================================================

def example_usage():
    """Пример использования рефакторированной архитектуры"""
    
    # 1. Настройка DI Container
    container = Container()
    container.config.from_yaml('config.yaml')
    
    # 2. Получение оркестратора через DI
    orchestrator = container.pipeline_orchestrator()
    
    # 3. Конфигурация полей для нормализации
    fields = [
        FieldConfig(
            name="chembl_id",
            data_type="string",
            normalization_type=NormalizationType.IDENTIFIER
        ),
        FieldConfig(
            name="canonical_smiles",
            data_type="string",
            normalization_type=NormalizationType.CHEMICAL,
            case_sensitive=True
        ),
        FieldConfig(
            name="pchembl_value",
            data_type="float",
            normalization_type=NormalizationType.NUMERIC,
            precision=2
        ),
    ]
    
    # 4. Запуск пайплайна
    result = orchestrator.run(
        config={
            "entity_name": "activity",
            "fields": fields,
            "batch_size": 10000,
        },
        output_path="/data/output/activity",
        streaming=True  # Для больших датасетов
    )
    
    print(f"Pipeline completed: {result}")


if __name__ == "__main__":
    example_usage()
