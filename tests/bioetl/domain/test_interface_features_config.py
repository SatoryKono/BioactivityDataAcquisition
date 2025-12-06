from bioetl.domain.configs.base import InterfaceFeaturesConfig


def test_provider_loader_port_flag_defaults_to_false() -> None:
    features = InterfaceFeaturesConfig()

    assert features.enable_provider_loader_port is False


def test_provider_loader_port_flag_can_be_enabled() -> None:
    features = InterfaceFeaturesConfig(enable_provider_loader_port=True)

    assert features.enable_provider_loader_port is True

