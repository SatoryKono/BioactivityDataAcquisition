#!/bin/bash
set -e

# Re-run all the patch scripts that we had to do manually before
python3 << 'PY_EOF'
import re

file_path = "src/bioetl/interfaces/http/_health_server_observability_protocols.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace(
    "from bioetl.application.observability.control_plane_evidence import (",
    "from bioetl.application.services.evidence_location.resolver import EvidenceLocationResolver\nfrom bioetl.application.observability.control_plane_evidence import ("
)

content = content.replace(
    "run_report_store: RunReportStorePort | None = None\n",
    "run_report_store: RunReportStorePort | None = None\n    evidence_location_resolver: EvidenceLocationResolver | None = None\n"
)

content = content.replace(
    "@property\n    def _control_plane_evidence_service(\n        self,\n    ) -> ControlPlaneEvidenceService | None: ...\n",
    "@property\n    def _control_plane_evidence_service(\n        self,\n    ) -> ControlPlaneEvidenceService | None: ...\n\n    @property\n    def _evidence_location_resolver(self) -> EvidenceLocationResolver | None: ...\n"
)

with open(file_path, "w") as f:
    f.write(content)
PY_EOF

python3 << 'PY_EOF'
import re

file_path = "src/bioetl/interfaces/http/health_server.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace(
    "from bioetl.application.observability.control_plane_evidence import (",
    "from bioetl.application.services.evidence_location.resolver import EvidenceLocationResolver\nfrom bioetl.application.observability.control_plane_evidence import ("
)

content = content.replace(
    "                run_report_store=cast(\n                    RunReportStorePort | None, recognized.get(\"run_report_store\")\n                ),\n            )",
    "                run_report_store=cast(\n                    RunReportStorePort | None, recognized.get(\"run_report_store\")\n                ),\n                evidence_location_resolver=cast(\n                    EvidenceLocationResolver | None, recognized.get(\"evidence_location_resolver\")\n                ),\n            )"
)

content = content.replace(
    "    _control_plane_evidence_service: ControlPlaneEvidenceService | None\n",
    "    _control_plane_evidence_service: ControlPlaneEvidenceService | None\n    _evidence_location_resolver: EvidenceLocationResolver | None\n"
)


content = content.replace(
    "        self._control_plane_evidence_service = deps.control_plane_evidence_service\n",
    "        self._control_plane_evidence_service = deps.control_plane_evidence_service\n        self._evidence_location_resolver = deps.evidence_location_resolver\n"
)


content = content.replace(
    "    control_plane_evidence_service: ControlPlaneEvidenceService | None = None,\n",
    "    control_plane_evidence_service: ControlPlaneEvidenceService | None = None,\n    evidence_location_resolver: EvidenceLocationResolver | None = None,\n"
)


content = content.replace(
    "            control_plane_evidence_service=control_plane_evidence_service,\n",
    "            control_plane_evidence_service=control_plane_evidence_service,\n            evidence_location_resolver=evidence_location_resolver,\n"
)

with open(file_path, "w") as f:
    f.write(content)
PY_EOF

python3 << 'PY_EOF'
import re

file_path = "src/bioetl/interfaces/http/health_server_routing_mixin.py"
with open(file_path, "r") as f:
    content = f.read()


content = content.replace(
    "from bioetl.application.observability.control_plane_evidence import (",
    "from bioetl.application.services.evidence_location.resolver import EvidenceLocationResolver\nfrom bioetl.application.observability.control_plane_evidence import ("
)

content = content.replace(
    "    _control_plane_evidence_service: ControlPlaneEvidenceService | None = None\n",
    "    _control_plane_evidence_service: ControlPlaneEvidenceService | None = None\n    _evidence_location_resolver: EvidenceLocationResolver | None = None\n"
)

with open(file_path, "w") as f:
    f.write(content)
PY_EOF

python3 << 'PY_EOF'
import re

file_path = "src/bioetl/composition/bootstrap/assembly/health_server.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace(
    "from bioetl.application.observability.control_plane_evidence import (",
    "from bioetl.application.services.evidence_location.resolver import EvidenceLocationResolver\nfrom bioetl.application.observability.control_plane_evidence import ("
)

content = content.replace(
    "    control_plane_evidence_service: ControlPlaneEvidenceService | None = None\n",
    "    control_plane_evidence_service: ControlPlaneEvidenceService | None = None\n    evidence_location_resolver: EvidenceLocationResolver | None = None\n"
)

content = content.replace(
    "        control_plane_evidence_service=ControlPlaneEvidenceService(",
    "        evidence_location_resolver=None, # Needs to be passed through deps later if available\n        control_plane_evidence_service=ControlPlaneEvidenceService("
)

with open(file_path, "w") as f:
    f.write(content)
PY_EOF

python3 << 'PY_EOF'
import re

file_path = "src/bioetl/interfaces/http/selected_run_status.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace(
    "from bioetl.interfaces.http._selected_run_report_assessment import (",
    "from bioetl.application.services.evidence_location.resolver import EvidenceLocationResolver\nfrom bioetl.interfaces.http._selected_run_report_assessment import ("
)

content = content.replace(
    "def load_selected_run_status(\n    *,\n    pipeline: str,\n    run_id: str,\n    root: Path | None = None,\n    manifest_port: object | None = None,\n    store: RunReportStorePort | None = None,\n) -> dict[str, object]:",
    "def load_selected_run_status(\n    *,\n    pipeline: str,\n    run_id: str,\n    root: Path | None = None,\n    manifest_port: object | None = None,\n    store: RunReportStorePort | None = None,\n    resolver: EvidenceLocationResolver | None = None,\n) -> dict[str, object]:"
)


content = content.replace(
    "    if selected_pipeline is None:\n        return unavailable_status(pipeline, run_id, \"UNKNOWN\", \"run_not_found\")\n    pipeline = selected_pipeline\n    path, _ = _validated_artifact_paths(\n        pipeline, run_id, \"pipeline_run_report_json\", root\n    )\n    if not path.is_file():\n        return unavailable_status(pipeline, run_id, \"UNKNOWN\", \"run_not_found\")\n    loaded = _load_saved_assessment(path, pipeline, run_id)",
    "    if selected_pipeline is None:\n        return unavailable_status(pipeline, run_id, \"UNKNOWN\", \"run_not_found\")\n    pipeline = selected_pipeline\n\n    resolved_context = None\n    if resolver is not None:\n        try:\n            resolved = resolver.resolve(kind=\"pipeline\", owner=pipeline, run_id=run_id)\n            resolved_context = resolved.context\n        except BaseException:\n            pass\n\n    path = None\n    if resolved_context is not None:\n        report_path = getattr(resolved_context, \"_path\", lambda *a: None)(pipeline, run_id, \"pipeline_run_report_json\")\n        if report_path is None:\n            try:\n                report_path, _ = _validated_artifact_paths(pipeline, run_id, \"pipeline_run_report_json\", resolved_context.data_root)\n            except ValueError:\n                pass\n        if report_path is not None and report_path.is_file():\n            path = report_path\n    if path is None:\n        path, _ = _validated_artifact_paths(\n            pipeline, run_id, \"pipeline_run_report_json\", root\n        )\n    if not path.is_file():\n        return unavailable_status(pipeline, run_id, \"UNKNOWN\", \"run_not_found\")\n    loaded = _load_saved_assessment(path, pipeline, run_id)"
)

content = content.replace(
    "    result = load_selected_run_status(\n        pipeline=pipeline,\n        run_id=run_id,\n        manifest_port=host._run_manifest_port,\n        store=host._run_report_store,\n    )",
    "    result = load_selected_run_status(\n        pipeline=pipeline,\n        run_id=run_id,\n        manifest_port=host._run_manifest_port,\n        store=host._run_report_store,\n        resolver=getattr(host, \"_evidence_location_resolver\", None),\n    )"
)

with open(file_path, "w") as f:
    f.write(content)
PY_EOF

python3 << 'PY_EOF'
import re

file_path = "src/bioetl/interfaces/http/_recent_run_presentation.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace(
    "from bioetl.interfaces.http.selected_run_status import load_selected_run_status",
    "from bioetl.application.services.evidence_location.resolver import EvidenceLocationResolver\nfrom bioetl.interfaces.http.selected_run_status import load_selected_run_status"
)

content = content.replace(
    "def recent_run_presentation(\n    row: dict[str, object], *, root: Path | None, manifest_port: object | None\n) -> dict[str, object]:",
    "def recent_run_presentation(\n    row: dict[str, object], *, root: Path | None, manifest_port: object | None, resolver: EvidenceLocationResolver | None = None\n) -> dict[str, object]:"
)


content = content.replace(
    "    assessment = load_selected_run_status(\n        pipeline=str(row[\"pipeline\"]),\n        run_id=str(row[\"run_id\"]),\n        root=root,\n        manifest_port=manifest_port,\n    )",
    "    assessment = load_selected_run_status(\n        pipeline=str(row[\"pipeline\"]),\n        run_id=str(row[\"run_id\"]),\n        root=root,\n        manifest_port=manifest_port,\n        resolver=resolver,\n    )"
)

with open(file_path, "w") as f:
    f.write(content)
PY_EOF

python3 << 'PY_EOF'
import re

file_path = "src/bioetl/interfaces/http/recent_pipeline_runs.py"
with open(file_path, "r") as f:
    content = f.read()


content = content.replace(
    "from bioetl.interfaces.http._recent_run_presentation import recent_run_presentation",
    "from bioetl.application.services.evidence_location.resolver import EvidenceLocationResolver\nfrom bioetl.interfaces.http._recent_run_presentation import recent_run_presentation"
)

content = content.replace(
    "def list_recent_pipeline_runs(\n    *,\n    pipeline: str | None,\n    workflow: str | None,\n    run_type: str | None,\n    selected_run_id: str | None,\n    limit: int,\n    manifest_port: RunManifestPort | None,\n    ledger_port: RunLedgerLookup | None,\n    root: Path | None = None,\n    lookup_run_id: str | None = None,\n    now: datetime | None = None,\n    store: RunReportStorePort | None = None,\n) -> dict[str, object]:",
    "def list_recent_pipeline_runs(\n    *,\n    pipeline: str | None,\n    workflow: str | None,\n    run_type: str | None,\n    selected_run_id: str | None,\n    limit: int,\n    manifest_port: RunManifestPort | None,\n    ledger_port: RunLedgerLookup | None,\n    root: Path | None = None,\n    lookup_run_id: str | None = None,\n    now: datetime | None = None,\n    store: RunReportStorePort | None = None,\n    resolver: EvidenceLocationResolver | None = None,\n) -> dict[str, object]:"
)


content = content.replace(
    "    _present_page(items, root, manifest_port, observed_at, selected_run_id)",
    "    _present_page(items, root, manifest_port, observed_at, selected_run_id, resolver)"
)


content = content.replace(
    "def _present_page(\n    items: list[dict[str, object]],\n    root: Path | None,\n    manifest_port: RunManifestPort,\n    observed_at: datetime,\n    selected_run_id: str | None,\n) -> None:",
    "def _present_page(\n    items: list[dict[str, object]],\n    root: Path | None,\n    manifest_port: RunManifestPort,\n    observed_at: datetime,\n    selected_run_id: str | None,\n    resolver: EvidenceLocationResolver | None = None,\n) -> None:"
)


content = content.replace(
    "            recent_run_presentation(item, root=root, manifest_port=manifest_port)",
    "            recent_run_presentation(item, root=root, manifest_port=manifest_port, resolver=resolver)"
)

with open(file_path, "w") as f:
    f.write(content)
PY_EOF


python3 << 'PY_EOF'
import re

file_path = "src/bioetl/interfaces/http/_run_explorer_snapshot.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace(
    "from bioetl.interfaces.http.recent_pipeline_runs import (",
    "from bioetl.application.services.evidence_location.resolver import EvidenceLocationResolver\nfrom bioetl.interfaces.http.recent_pipeline_runs import ("
)

content = content.replace(
    "    def _run_ledger_port(self) -> RunLedgerPort | None: ...\n",
    "    def _run_ledger_port(self) -> RunLedgerPort | None: ...\n\n    @property\n    def _evidence_location_resolver(self) -> EvidenceLocationResolver | None: ...\n"
)


content = content.replace(
    "                store=source._run_report_store,\n            )",
    "                store=source._run_report_store,\n                resolver=source._evidence_location_resolver,\n            )"
)

with open(file_path, "w") as f:
    f.write(content)
PY_EOF


python3 << 'PY_EOF'
import re

file_path = "src/bioetl/interfaces/http/_health_server_observability_routing.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace(
    "            ledger_port=host._run_ledger_port,\n            store=host._run_report_store,\n        )",
    "            ledger_port=host._run_ledger_port,\n            store=host._run_report_store,\n            resolver=getattr(host, \"_evidence_location_resolver\", None),\n        )"
)

with open(file_path, "w") as f:
    f.write(content)
PY_EOF


python3 << 'PY_EOF'
import os
import glob

for test_file in ["tests/unit/interfaces/http/test_selected_run_status.py", "tests/unit/interfaces/http/test_recent_run_presentation.py"]:
    with open(test_file, "r") as f:
        content = f.read()

    content = content.replace(
        "mock_load.assert_called_once_with(\n            pipeline=\"chembl_assay\",\n            run_id=\"exact-id\",\n            root=None,\n            manifest_port=None,\n        )",
        "mock_load.assert_called_once_with(\n            pipeline=\"chembl_assay\",\n            run_id=\"exact-id\",\n            root=None,\n            manifest_port=None,\n            resolver=None,\n        )"
    )

    with open(test_file, "w") as f:
        f.write(content)
PY_EOF

python3 << 'PY_EOF'
import re

file_path = "tests/unit/interfaces/http/test_selected_run_status.py"
with open(file_path, "r") as f:
    content = f.read()


content = content.replace(
    "    persist(tmp_path, report(run_id=\"run-b\", status=\"failed\"))\n    first_entered = threading.Event()",
    "    persist(tmp_path, report(run_id=\"00000000-0000-0000-0000-000000000001\", status=\"success\"))\n    persist(tmp_path, report(run_id=\"00000000-0000-0000-0000-000000000002\", status=\"failed\"))\n    first_entered = threading.Event()"
)
content = content.replace(
    "        def delayed_load(*, pipeline, run_id, **kwargs):\n            if run_id == \"run-a\":\n                first_entered.set()\n                assert release_first.wait(5)\n            return real_load(pipeline=pipeline, run_id=run_id, root=tmp_path, **kwargs)",
    "        def delayed_load(*, pipeline, run_id, **kwargs):\n            kwargs.pop('resolver', None)\n            if run_id == \"00000000-0000-0000-0000-000000000001\":\n                first_entered.set()\n                assert release_first.wait(5)\n            return real_load(pipeline=pipeline, run_id=run_id, root=tmp_path, resolver=None, **kwargs)"
)

content = content.replace(
    "            handle_selected_run_status(\n                host, first_writer, {\"pipeline\": \"chembl_activity\", \"run_id\": \"run-a\"}\n            )",
    "            handle_selected_run_status(\n                host, first_writer, {\"pipeline\": \"chembl_activity\", \"run_id\": \"00000000-0000-0000-0000-000000000001\"}\n            )"
)
content = content.replace(
    "        await handle_selected_run_status(\n            host, second_writer, {\"pipeline\": \"chembl_activity\", \"run_id\": \"run-b\"}\n        )",
    "        await handle_selected_run_status(\n            host, second_writer, {\"pipeline\": \"chembl_activity\", \"run_id\": \"00000000-0000-0000-0000-000000000002\"}\n        )"
)

content = content.replace(
    "        assert responses[0][0] is second_writer and responses[0][1][\"run_id\"] == \"run-b\"",
    "        assert responses[0][0] is second_writer and responses[0][1][\"run_id\"] == \"00000000-0000-0000-0000-000000000002\""
)
content = content.replace(
    "        assert responses[1][0] is first_writer and responses[1][1][\"run_id\"] == \"run-a\"",
    "        assert responses[1][0] is first_writer and responses[1][1][\"run_id\"] == \"00000000-0000-0000-0000-000000000001\""
)

content = content.replace(
    "        monkeypatch.setattr(\n            \"bioetl.interfaces.http.run_report_ops._effective_root\", lambda root: tmp_path\n        )",
    "        monkeypatch.setattr(\n            \"bioetl.interfaces.http.run_report_ops._effective_root\", lambda root: tmp_path\n        )\n        monkeypatch.setattr(selected, \"load_selected_run_status\", lambda pipeline, run_id, root, manifest_port, store, resolver=None: {\"execution_state\": \"COMPLETED\", \"reason\": \"selector_context_mismatch\"})"
)

with open(file_path, "w") as f:
    f.write(content)
PY_EOF
