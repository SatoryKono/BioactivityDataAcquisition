# Logging Module Diagram

## Class Diagram

```mermaid
graph TB
    subgraph "ABC Contracts"
        LA[LoggerAdapterABC<br/>+info<br/>+error<br/>+debug<br/>+warning<br/>+bind]
        PA[ProgressReporterABC<br/>+start<br/>+update<br/>+finish<br/>+create_bar]
        TA[TracerABC<br/>+start_span<br/>+end_span<br/>+inject_context]
    end
    
    subgraph "Implementations"
        UL[UnifiedLoggerImpl<br/>-_logger: BoundLogger<br/>implements LoggerAdapterABC]
        TP[TqdmProgressReporterImpl<br/>-_pbar: tqdm<br/>implements ProgressReporterABC]
    end
    
    LA -.->|implements| UL
    PA -.->|implements| TP
    
    style LA fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style PA fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style TA fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style UL fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style TP fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

## Module Structure

```mermaid
graph TB
    subgraph "Contracts"
        LA[LoggerAdapterABC]
        PA[ProgressReporterABC]
        TA[TracerABC]
    end
    
    subgraph "Factories"
        DL[default_logger]
        DPR[default_progress_reporter]
    end
    
    subgraph "Implementations"
        UL[UnifiedLoggerImpl]
        TP[TqdmProgressReporterImpl]
    end
    
    DL --> UL
    DPR --> TP
    UL -.-> LA
    TP -.-> PA
    
    style LA fill:#e1f5ff,stroke:#01579b
    style PA fill:#e1f5ff,stroke:#01579b
    style TA fill:#e1f5ff,stroke:#01579b
    style UL fill:#fff3e0,stroke:#e65100
    style TP fill:#fff3e0,stroke:#e65100
```

## File Structure

```text
src/bioetl/infrastructure/logging/
├── contracts.py          # ABC interfaces
├── factories.py         # Default factory functions
└── impl/
    ├── unified_logger.py        # LoggerAdapterABC implementation
    └── progress_reporter.py     # ProgressReporterABC implementation
```

## Как просмотреть диаграмму

### В Cursor

**Важно**: Cursor может не поддерживать все типы диаграмм Mermaid. Если диаграммы не отображаются:

1. **Markdown Preview**:
   - Откройте файл
   - Нажмите `Ctrl+Shift+V` (Windows/Linux) или `Cmd+Shift+V` (Mac)
   - Или используйте команду "Markdown: Open Preview" из палитры команд (`Ctrl+Shift+P`)

2. **Проверка расширений**:
   - Убедитесь, что установлено расширение "Markdown Preview Mermaid Support" или "Markdown Preview Enhanced"
   - Перезапустите Cursor после установки расширения

3. **Альтернатива**: Используйте онлайн-редактор Mermaid (см. ниже)

### Альтернативные способы

- **Mermaid Live Editor**: [mermaid.live](https://mermaid.live/) — скопируйте код из блока `mermaid` и вставьте в редактор
- **GitHub/GitLab**: Диаграммы автоматически рендерятся в markdown файлах на GitHub/GitLab
- **VS Code**: Расширение "Markdown Preview Mermaid Support"
- **Obsidian**: Встроенная поддержка Mermaid диаграмм
