from scripts.engineering.qa.hotspot_family_metrics import collect_hotspot_family_metrics

for item in collect_hotspot_family_metrics(active_only=False):
    if item.name == "composition_factories_pipeline":
        print(item.to_dict())
        break
