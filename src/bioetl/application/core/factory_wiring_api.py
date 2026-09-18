"""Legacy flat facade for composition-owned pipeline factory wiring."""

from __future__ import annotations

from bioetl.application.core.wiring.factory import (
    BasePipeline as BasePipeline,
)
from bioetl.application.core.wiring.factory import (
    BatchExecutor as BatchExecutor,
)
from bioetl.application.core.wiring.factory import (
    CheckpointRuntimeService as CheckpointRuntimeService,
)
from bioetl.application.core.wiring.factory import (
    LockRuntimeService as LockRuntimeService,
)
from bioetl.application.core.wiring.factory import (
    PipelineRunner as PipelineRunner,
)
from bioetl.application.core.wiring.factory import (
    PipelineRunnerDependencies as PipelineRunnerDependencies,
)
from bioetl.application.core.wiring.factory import (
    PipelineService as PipelineService,
)
from bioetl.application.core.wiring.factory import (
    PostrunService as PostrunService,
)
from bioetl.application.core.wiring.factory import (
    PreflightService as PreflightService,
)
from bioetl.application.core.wiring.factory import (
    ShutdownSignal as ShutdownSignal,
)
from bioetl.application.core.wiring.factory import __all__ as __all__
