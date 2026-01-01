
import ast
from pathlib import Path

class TestClassSize:
    MAX_CLASS_LINES = 300
    EXEMPTIONS = {
        "BasePipeline": 400,
        "PipelineRunner": 450,
        "UnifiedHTTPClient": 400,
        "PipelineObserver": 350,
        "StorageAdapter": 520,
        "BaseTransformer": 580,
        "SilverWriter": 830,
        "GoldWriter": 720,
        "MedallionLifecycleService": 385,
        "LineageTracker": 400,
        "ChemblAdapter": 520,
        "GenericPipelineFactory": 350,
        "PreflightService": 545,
        "PostrunService": 355,
        "BronzeWriter": 600,
        "BatchExecutor": 600,
        "BatchWriter": 350,
        "CrossRefAdapter": 460,
        "PubChemAdapter": 310,
        "CrossRefTransformer": 360,
        "UniProtAdapter": 320,
        "PubMedAdapter": 360,
        "ErrorService": 420,
        "NormalizationService": 370,
        "ActivityAggregator": 320,
        "ValueValidator": 320,
        "Batch": 450,
        "PipelineRun": 420,
        "QuarantineEntry": 430,
        "TestCliCommands": 350,
        "TestFileSizeLimits": 350,
        "TestFunctionComplexity": 350,
        "TestFunctionLength": 350,
        "TestClassSize": 350,
        "MedallionConfigValidator": 350,
    }

    def check(self, src_dir: Path):
        bioetl_path = src_dir / "src/bioetl"
        if not bioetl_path.exists():
            print(f"bioetl not found at {bioetl_path}")
            return

        violations = []

        for py_file in bioetl_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    class_lines = end_line - start_line + 1

                    max_lines = self.EXEMPTIONS.get(node.name, self.MAX_CLASS_LINES)

                    if class_lines > max_lines:
                        violations.append(
                            f"{py_file.name}:{start_line} - {node.name} "
                            f"is {class_lines} lines (max={max_lines})"
                        )

        if violations:
            print("Classes exceeding line limit:")
            for v in violations:
                print(f"  - {v}")
        else:
            print("No violations found.")

if __name__ == "__main__":
    TestClassSize().check(Path("."))
