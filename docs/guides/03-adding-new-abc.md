# Adding New ABC

Руководство по расширению системы контрактов. Используйте **Трёхслойный паттерн** (ABC / Default / Impl).

## Шаг 1. Определение контракта (ABC)
Создайте абстрактный класс в файле `contracts.py`. Обязательно добавьте docstring со структурой.

```python
# src/bioetl/clients/base/contracts.py
class NewFeatureABC(ABC):
    """
    Краткое описание функциональности.

    Public Interface:
        do_work(param: str) -> Result

    Localization:
        - Contract: src/bioetl/clients/base/contracts.py
        - Default: src/bioetl/clients/base/factories.py::default_new_feature()
        - Impl: src/bioetl/clients/base/impl/new_feature_impl.py
    """

    @abstractmethod
    def do_work(self, param: str) -> Result:
        ...
```

## Шаг 2. Фабрика по умолчанию (Default)
Создайте функцию-фабрику в `factories.py`. Она может возвращать заглушку или `NotImplementedError`, пока нет реализации.

```python
# src/bioetl/clients/base/factories.py
def default_new_feature() -> NewFeatureABC:
    raise NotImplementedError("No default implementation yet")
```

## Шаг 3. Регистрация
Обновите реестры.

**src/bioetl/clients/base/abc_registry.yaml**:
```yaml
NewFeatureABC:
  module: bioetl.clients.base.contracts
  default_factory: bioetl.clients.base.factories.default_new_feature
```

**src/bioetl/clients/base/abc_impls.yaml**:
```yaml
NewFeatureABC:
  default: default_new_feature
  impls: []
```

## Шаг 4. Документация
Добавьте новый ABC в таблицу каталога `docs/reference/abc/00-index.md`.

