# stdlib
from typing import Any

# third party
import numpy as np
import pandas as pd
import pytest

# autoprognosis absolute
from autoprognosis.plugins.imputers import ImputerPlugin, Imputers
from autoprognosis.plugins.imputers.plugin_EM import plugin
from autoprognosis.plugins.utils.metrics import RMSE
from autoprognosis.plugins.utils.simulate import simulate_nan


def from_api() -> ImputerPlugin:
    return Imputers().get("EM")


def from_module() -> ImputerPlugin:
    return plugin()


def from_serde() -> ImputerPlugin:
    buff = plugin().save()
    return plugin.load(buff)


@pytest.mark.parametrize("test_plugin", [from_api(), from_module(), from_serde()])
def test_em_plugin_sanity(test_plugin: ImputerPlugin) -> None:
    assert test_plugin is not None


@pytest.mark.parametrize("test_plugin", [from_api(), from_module(), from_serde()])
def test_em_plugin_name(test_plugin: ImputerPlugin) -> None:
    assert test_plugin.name() == "EM"


@pytest.mark.parametrize("test_plugin", [from_api(), from_module(), from_serde()])
def test_em_plugin_type(test_plugin: ImputerPlugin) -> None:
    assert test_plugin.type() == "imputer"


@pytest.mark.parametrize("test_plugin", [from_api(), from_module(), from_serde()])
def test_em_plugin_hyperparams(test_plugin: ImputerPlugin) -> None:
    assert len(test_plugin.hyperparameter_space()) == 2


@pytest.mark.parametrize("test_plugin", [from_api(), from_module(), from_serde()])
def test_em_plugin_fit_transform(test_plugin: ImputerPlugin) -> None:
    res = test_plugin.fit_transform(
        pd.DataFrame(
            [[1, 1, 1, 1], [np.nan, np.nan, np.nan, np.nan], [3, 3, 9, 9], [2, 2, 2, 2]]
        )
    )

    assert not np.all(np.isnan(res))


@pytest.mark.parametrize("test_plugin", [from_api(), from_module(), from_serde()])
@pytest.mark.parametrize("mechanism", ["MAR"])
@pytest.mark.parametrize("p_miss", [0.5])
@pytest.mark.parametrize(
    "other_plugin",
    [Imputers().get("mean"), Imputers().get("median"), Imputers().get("most_frequent")],
)
def test_compare_methods_perf(
    test_plugin: ImputerPlugin, mechanism: str, p_miss: float, other_plugin: Any
) -> None:
    np.random.seed(0)

    n = 10
    p = 4

    mean = np.repeat(0, p)
    cov = 0.5 * (np.ones((p, p)) + np.eye(p))

    x = np.random.multivariate_normal(mean, cov, size=n)
    x_simulated = simulate_nan(x, p_miss, mechanism)

    mask = x_simulated["mask"]
    x_miss = pd.DataFrame(x_simulated["X_incomp"])

    x_em = test_plugin.fit_transform(x_miss)
    rmse_em = RMSE(x_em.to_numpy(), x, mask)

    x_other = other_plugin.fit_transform(x_miss)
    rmse_other = RMSE(x_other.to_numpy(), x, mask)

    assert rmse_em < rmse_other
