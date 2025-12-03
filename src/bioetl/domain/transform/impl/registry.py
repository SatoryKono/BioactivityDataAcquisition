"""
Registry for field normalizers.
"""
from typing import Any, Callable

from bioetl.domain.transform.contracts import FieldNormalizerABC


class FunctionFieldNormalizer(FieldNormalizerABC):
    """
    Адаптер для функциональных нормализаторов.
    """
    
    def __init__(self, func: Callable[[Any], Any]):
        self._func = func
        
    def normalize(self, value: Any) -> Any:
        return self._func(value)


class NormalizerRegistry:
    """
    Реестр нормализаторов полей.
    """
    
    def __init__(self) -> None:
        self._normalizers: dict[str, FieldNormalizerABC] = {}
        self._case_sensitive_fields: set[str] = set()
        self._id_fields: set[str] = set()

    def register(self, field_name: str, normalizer: FieldNormalizerABC | Callable[[Any], Any]) -> None:
        """Регистрирует нормализатор для поля."""
        if isinstance(normalizer, FieldNormalizerABC):
            self._normalizers[field_name] = normalizer
        else:
            self._normalizers[field_name] = FunctionFieldNormalizer(normalizer)

    def get(self, field_name: str) -> FieldNormalizerABC | None:
        """Возвращает нормализатор для поля."""
        return self._normalizers.get(field_name)

    def set_case_sensitive_fields(self, fields: list[str]) -> None:
        """Устанавливает список полей, чувствительных к регистру."""
        self._case_sensitive_fields = set(fields)

    def set_id_fields(self, fields: list[str]) -> None:
        """Устанавливает список полей-идентификаторов."""
        self._id_fields = set(fields)

    def is_case_sensitive(self, field_name: str) -> bool:
        """Проверяет, чувствительно ли поле к регистру."""
        return field_name in self._case_sensitive_fields

    def is_id_field(self, field_name: str) -> bool:
        """Проверяет, является ли поле идентификатором."""
        if field_name in self._id_fields:
            return True
        if field_name.endswith("_id") or field_name.endswith("_chembl_id"):
            return True
        if field_name.startswith("id_"):
            return True
        return False

