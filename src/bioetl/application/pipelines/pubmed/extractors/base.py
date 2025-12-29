"""Base class for PubMed XML field extractors.

Implements Template Method pattern for consistent extraction process.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from xml.etree.ElementTree import Element


class BaseFieldExtractor(ABC):
    """Template Method для извлечения полей из PubMed XML.

    Наследники реализуют extract() и normalize() для конкретных полей.
    Метод process() объединяет их в единый процесс обработки.

    Example:
        >>> class MyExtractor(BaseFieldExtractor):
        ...     def extract(self, element):
        ...         return element.find("MyField").text
        ...     def normalize(self, raw_value):
        ...         return raw_value.strip().upper()
        >>> extractor = MyExtractor()
        >>> result = extractor.process(some_element)
    """

    @abstractmethod
    def extract(self, element: Element | None) -> Any:
        """Извлечь сырые данные из XML элемента.

        Args:
            element: XML элемент для извлечения данных.

        Returns:
            Сырые данные (могут быть None, строкой, списком и т.д.).
        """
        ...

    @abstractmethod
    def normalize(self, raw_value: Any) -> Any:
        """Нормализовать извлечённое значение.

        Args:
            raw_value: Сырое значение из extract().

        Returns:
            Нормализованное значение.
        """
        ...

    def process(self, element: Element | None) -> Any:
        """Template method: extract → normalize.

        Выполняет полный цикл извлечения и нормализации данных.

        Args:
            element: XML элемент для обработки.

        Returns:
            Нормализованное значение или None.
        """
        raw = self.extract(element)
        return self.normalize(raw) if raw is not None else None
