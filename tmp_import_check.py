import tests.e2e.test_e2e_stability_policy as m

print(
    "ok",
    hasattr(
        m,
        "test_deferred_matrix_cases_are_excluded_from_default_smoke_parametrization",
    ),
)
