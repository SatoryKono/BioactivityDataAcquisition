  План рефакторинга для RF-006

  Цель рефакторинга: сузить composite runtime так, чтобы orchestration policy, runtime assembly и execution plumbing перестали быть слеплены в два перегруженных узла. Ключевая идея здесь не “разнести всё по новым
  файлам”, а восстановить читаемые seams: dependency_coordinator должен заниматься только ходом выполнения зависимостей, а composite_support_services_factory только сборкой графа зависимостей из более мелких
  фабрик. При этом runner.py не надо делать центральной точкой новой сложности; наоборот, после сужения coordinator/factory runner должен остаться тонким потребителем новых фасадов.

  Первый этап: зафиксировать текущее поведение characterization-тестами. Нужны отдельные тесты на stop conditions, resume/skip semantics, timeout mapping, failed dependency result mapping и completed-dependency
  marking для dependency_coordinator.py. Это даст свободу двигать код без регрессии в composite runtime, где ошибка обычно проявляется не сразу, а на длинной цепочке зависимостей. Параллельно нужно покрыть smoke-
  сценариями сборку из composite_support_services_factory.py, чтобы фиксировать не внутреннюю реализацию, а ожидаемые contracts собранных объектов.

  Второй этап: декомпозировать dependency_coordinator по ответственности. Вынести в отдельные application-level collaborators три куска: DependencyExecutionPlanner для выбора следующего dependency step и stop
  conditions, DependencyResultMapper для перевода timeout/exception/success в единый typed result, и DependencyProgressTracker для completed/failed bookkeeping. Сам coordinator после этого должен хранить только
  основной цикл исполнения и вызовы этих сервисов. Локальные top-level helper functions нужно не просто “переложить в util”, а распределить по новым модулям по смыслу. Логирование и tracing желательно оставить на
  boundary coordinator-а, чтобы policy classes были максимально детерминированными и легко тестируемыми.

  Третий этап: разрезать fat factory. Вместо одного большого composite_support_services_factory.py ввести 2-3 подфабрики: composite_dependency_runtime_factory.py, composite_merge_runtime_factory.py,
  composite_observability_runtime_factory.py. Главная фабрика остаётся только как facade, который собирает итоговый runtime context. Это уменьшит blast radius изменений: модификация merge path не должна требовать
  чтения dependency/runtime graph целиком. Важно вынести из текущей фабрики скрытые policy-константы и оформить их как именованные настройки или отдельный config object, иначе композиционный слой продолжит тащить
  бизнес-решения в коде.

  Четвёртый этап: минимально адаптировать runner. Если после декомпозиции runner.py всё ещё знает слишком много о промежуточных деталях coordinator-а, ему нужен один новый фасадный dependency type, а не
  дополнительные helper-методы. Цель не в том, чтобы ещё сильнее дробить runner mixin-ами, а в том, чтобы runner зависел от узких interfaces composite runtime.

  Негативная цель: не переносить composition logic в application и не размазывать orchestration policy по “utils”. Критерий завершения: coordinator заметно меньше по числу веток и helper-обязанностей; factory
  собирает runtime через подфабрики; runner не растёт; unit tests покрывают policy seams отдельно, а integration tests composite runtime остаются зелёными.

  План рефакторинга для RF-008

  Этот рефакторинг нужно вести в правильном порядке: сначала вернуть надёжный E2E signal, потом нормализовать CLI hotspot, затем выпрямить provider adapters. Если начать с переписывания openalex/client.py или
  crossref/client.py без рабочего верхнеуровневого сигнала, проект получит churn без уверенности, что orchestration действительно не сломана. Поэтому первым deliverable должен стать новый, устойчивый
  верхнеуровневый test pyramid для CLI/provider flows.

  Этап 1: разделить “E2E” и “system/infrastructure” тесты. Текущий test_full_pipeline.py сам показывает, что сигнал ненадёжен: реальные внешние зависимости, Docker-bound setup и текущий skip. Это нужно разрезать на
  два уровня. Первый уровень: deterministic local E2E smoke, который прогоняет критический пользовательский путь через CLI/runtime с локальными или fake adapters и локальным storage, без Docker и сети. Второй
  уровень: опциональные system tests с реальной инфраструктурой, которые не блокируют базовый engineering feedback loop. После этого любой рефакторинг run_all и provider clients можно валидировать не только unit/
  integration, но и реальным верхнеуровневым smoke.

  Этап 2: истончить run_all.py. Сейчас этот модуль одновременно решает discovery, filtering, destructive confirmation, health server lifecycle, orchestration async execution, result rendering и exit-code policy.
  Его нужно разрезать как минимум на три части: run_all_planner.py для выбора pipeline set и execution plan, run_all_executor.py для async orchestration и lifecycle, run_all_presenter.py для table/output/exit
  summary. CLI-команда должна остаться тонким adapter layer: разобрать аргументы, вызвать planner/executor, отрендерить результат. Это сократит связанность с UX и упростит тестирование без запуска всего Click
  stack.

  Этап 3: нормализовать OpenAlex adapter. В openalex/client.py всё ещё смешаны default dependency builders, runtime adapter logic и policy decisions по retries/fallback/pagination. Их надо развести: composition-
  like default builders вынести в отдельный module, например openalex/defaults.py или factory в composition/infrastructure boundary; runtime client оставить как тонкий adapter, который зависит от уже собранных
  collaborators. Это сделает модуль симметричнее остальным адаптерам и уменьшит hidden wiring внутри инфраструктурного класса.

  Этап 4: выровнять CrossRef по той же схеме, но без переписывания ради переписывания. crossref/client.py уже лучше структурирован, поэтому здесь нужен не большой разрез, а alignment: одинаковые naming conventions,
  одинаковый подход к defaults/wiring, единый pattern для pagination/retry/error translation там, где это реально совпадает с OpenAlex.

  Критично зафиксировать non-goals. Не нужно одновременно менять provider semantics, pagination contracts и CLI UX. Не нужно объединять OpenAlex и CrossRef в один generic mega-client. Цель именно в нормализации
  seams и в восстановлении trustable signal. Критерий завершения: есть стабильный local E2E smoke; run_all.py стал thin command module; OpenAlex больше не играет роль скрытого composition root; CrossRef выровнен по
  паттернам без лишнего churn; refactor safety обеспечен тестами на planner/executor/client contracts и одним верхнеуровневым smoke.

  Если нужно, следующим сообщением разверну эти два плана в task breakdown по файлам и тестам.