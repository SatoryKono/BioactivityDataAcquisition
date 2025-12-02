# 02 CLI Command ABC

## Описание

CLICommandABC определяет интерфейс для плагинных команд CLI, связанных с пайплайнами. Каждая команда имеет имя и метод выполнения, который принимает аргументы командной строки и возвращает код выхода. Это позволяет расширять CLI функциональность без изменения базового кода оркестратора.

## Interface

```python
from abc import ABC, abstractmethod

class CLICommandABC(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Имя команды CLI."""
        ...

    @abstractmethod
    def run(self, args: list[str]) -> int:
        """Выполнить команду с аргументами. Возвращает код выхода."""
        ...
```

## Related Components

- **PipelineBase**: использует команды для выполнения пайплайнов
- **ConfigResolverABC**: может использоваться командами для загрузки конфигурации

