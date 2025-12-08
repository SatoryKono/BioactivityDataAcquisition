from bioetl.domain.configs import InterfaceFeaturesConfig


def test_rest_interface_flag_defaults_to_false() -> None:
    features = InterfaceFeaturesConfig()

    assert features.rest_interface_enabled is False


def test_rest_interface_flag_can_be_enabled() -> None:
    features = InterfaceFeaturesConfig(rest_interface_enabled=True)

    assert features.rest_interface_enabled is True


def test_mq_interface_flag_defaults_to_false() -> None:
    features = InterfaceFeaturesConfig()

    assert features.mq_interface_enabled is False


def test_mq_interface_flag_can_be_enabled() -> None:
    features = InterfaceFeaturesConfig(mq_interface_enabled=True)

    assert features.mq_interface_enabled is True
