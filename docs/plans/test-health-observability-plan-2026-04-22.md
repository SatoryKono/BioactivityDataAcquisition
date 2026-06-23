 Изучи дизайн, layout и представление данных в Grafana dashboard `BioETL  3. provider-health`.

  Цель:
  Не вносить изменения автоматически. Провести визуально-структурный аудит dashboard и подготовить конкретный план исправлений.

  Что нужно проверить:

  1. Общий layout и композиция
  - Логика первого экрана: какие панели видны без прокрутки.
  - Насколько первый экран отвечает на главный операторский вопрос dashboard.
  - Порядок секций и row-групп: соответствует ли он expected operator flow.
  - Баланс плотности: нет ли перегруженных зон и нет ли чрезмерно пустых областей.
  - Использование пространства:
    - есть ли большие пустые участки;
    - есть ли панели с неэффективной шириной/высотой;
    - можно ли уплотнить layout без потери читаемости.
  - Визуальная согласованность размеров панелей, row headers, отступов, alignment.

  2. Расположение панелей
  - Проверить координаты и размеры всех panels (`gridPos`).
  - Найти:
    - неиспользуемое пустое пространство;
    - дисбаланс по ширине между связанными панелями;
    - панели, которые логически должны стоять рядом, но разнесены;
    - секции, где лучше изменить порядок panel placement.
  - Оценить, не скрыты ли важные critical panels слишком низко или внутри collapsed rows.

  3. Представление данных в панелях
  Для каждой панели проверить:
  - title, type, datasource;
  - достаточно ли места для визуализации данных;
  - не обрезаются ли значения, legends, labels, column names, status texts;
  - читаемы ли thresholds, mappings, units, descriptions;
  - корректно ли panel type соответствует данным;
  - достаточно ли ширины/высоты для table/timeseries/stat panel;
  - нет ли panel overcrowding, когда слишком много series/columns/labels для текущего размера.

  4. Видимость каждого поля
  Особенно важно проверить для table и timeseries panels:
  - видны ли все ключевые поля/колонки;
  - не скрываются ли важные labels в legend;
  - не слишком ли длинные titles/legend labels;
  - не требуется ли resize panel или change display mode;
  - есть ли панели, где данные technically correct, но practically unreadable.
  Если live UI недоступен, сделай repo-first аудит по JSON-конфигу и явно отметь ограничения.

  5. UX и операторская пригодность
  - Понятен ли текущий state dashboard без дополнительных кликов.
  - Не создаёт ли layout ложный акцент на второстепенных панелях.
  - Есть ли панели, которые лучше перенести выше/ниже.
  - Есть ли дублирование информации между panels.
  - Есть ли панели, которые слишком большие для своей ценности или слишком маленькие для своих данных.

  Формат результата:

  1. Краткий вывод
  - Общая оценка layout и usability.
  - Можно ли считать dashboard визуально эффективным для operator triage.

  2. Findings
  Для каждого замечания укажи:
  - Severity: HIGH / MEDIUM / LOW
  - Panel ID и title
  - Что именно не так в layout или visibility
  - Почему это проблема
  - Как лучше исправить

  3. Таблица по всем панелям
  Для каждой панели:
  - Panel ID
  - Title
  - Status: OK / Needs Resize / Needs Reposition / Needs Review
  - Краткий комментарий

  4. План правок
  Сформируй phased remediation plan:
  - Phase 1: critical layout/visibility fixes
  - Phase 2: spacing and composition improvements
  - Phase 3: polish and consistency fixes
  Для каждой правки укажи:
  - файл
  - panel ID
  - что менять в `gridPos` / panel size / ordering / display settings
  - ожидаемый эффект

  5. Ограничения
  - Что удалось проверить статически
  - Что требует live Grafana/browser review
  - Какие выводы являются confidence-high, а какие confidence-medium

  Важно:
  - Ничего не исправляй автоматически.
  - Не ограничивайся PromQL или correctness audit.
  - Фокус именно на layout, panel placement, readability, empty space, field visibility и operator usability.

