from bioetl.infrastructure.quality.exemptions_registry import load_exemptions_registry
import bioetl.infrastructure.quality.exemptions_registry as mod
print('module', mod.__file__)
raw = load_exemptions_registry()
cs = raw.get('registries', {}).get('class_size', {})
print('count', len(cs))
for k in sorted(cs):
    print(k)
