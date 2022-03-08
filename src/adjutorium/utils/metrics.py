# stdlib
from typing import Tuple, Union

# third party
import numpy as np
import pandas as pd
from sklearn.metrics import (
    auc,
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import label_binarize

# adjutorium absolute
import adjutorium.logger as log
from adjutorium.utils.third_party.metrics import brier_score, concordance_index_ipcw


def get_y_pred_proba_hlpr(y_pred_proba: np.ndarray, nclasses: int) -> np.ndarray:
    if nclasses == 2:
        if len(y_pred_proba.shape) < 2:
            return y_pred_proba

        if y_pred_proba.shape[1] == 2:
            return y_pred_proba[:, 1]

    return y_pred_proba


def evaluate_auc(
    y_test: np.ndarray,
    y_pred_proba: np.ndarray,
    classes: Union[np.ndarray, None] = None,
) -> Tuple[float, float]:

    y_test = np.asarray(y_test)
    y_pred_proba = np.asarray(y_pred_proba)

    nnan = sum(np.ravel(np.isnan(y_pred_proba)))

    if nnan:
        raise ValueError("nan in predictions. aborting")

    n_classes = len(set(np.ravel(y_test)))

    y_pred_proba_tmp = get_y_pred_proba_hlpr(y_pred_proba, n_classes)

    if n_classes > 2:

        log.debug(f"+evaluate_auc {y_test.shape} {y_pred_proba_tmp.shape}")

        fpr = dict()
        tpr = dict()
        precision = dict()
        recall = dict()
        average_precision = dict()
        roc_auc: dict = dict()

        if classes is None:
            classes = sorted(set(np.ravel(y_test)))
            log.debug(
                "warning: classes is none and more than two "
                " (#{}), classes assumed to be an ordered set:{}".format(
                    n_classes, classes
                )
            )

        y_test = label_binarize(y_test, classes=classes)

        fpr["micro"], tpr["micro"], _ = roc_curve(
            y_test.ravel(), y_pred_proba_tmp.ravel()
        )
        roc_auc["micro"] = auc(fpr["micro"], tpr["micro"])

        precision["micro"], recall["micro"], _ = precision_recall_curve(
            y_test.ravel(), y_pred_proba_tmp.ravel()
        )

        average_precision["micro"] = average_precision_score(
            y_test, y_pred_proba_tmp, average="micro"
        )

        aucroc = roc_auc["micro"]
        aucprc = average_precision["micro"]
    else:

        aucroc = roc_auc_score(np.ravel(y_test), y_pred_proba_tmp, multi_class="ovr")
        aucprc = average_precision_score(np.ravel(y_test), y_pred_proba_tmp)

    return aucroc, aucprc


def evaluate_skurv_c_index(
    T_train: np.ndarray,
    Y_train: np.ndarray,
    Prediction: np.ndarray,
    T_test: np.ndarray,
    Y_test: np.ndarray,
    Time: float,
) -> float:
    T_train = pd.Series(T_train)
    Y_train = pd.Series(Y_train)
    T_test = pd.Series(T_test)
    Y_test = pd.Series(Y_test)

    Y_train_structured = [
        (Y_train.iloc[i], T_train.iloc[i]) for i in range(len(Y_train))
    ]
    Y_train_structured = np.array(
        Y_train_structured, dtype=[("status", "bool"), ("time", "<f8")]
    )

    Y_test_structured = [(Y_test.iloc[i], T_test.iloc[i]) for i in range(len(Y_test))]
    Y_test_structured = np.array(
        Y_test_structured, dtype=[("status", "bool"), ("time", "<f8")]
    )

    # concordance_index_ipcw expects risk scores
    return concordance_index_ipcw(
        Y_train_structured, Y_test_structured, Prediction, tau=Time
    )


def evaluate_skurv_brier_score(
    T_train: np.ndarray,
    Y_train: np.ndarray,
    Prediction: np.ndarray,
    T_test: np.ndarray,
    Y_test: np.ndarray,
    Time: float,
) -> float:
    T_train = pd.Series(T_train)
    Y_train = pd.Series(Y_train)
    T_test = pd.Series(T_test)
    Y_test = pd.Series(Y_test)

    Y_train_structured = [
        (Y_train.iloc[i], T_train.iloc[i]) for i in range(len(Y_train))
    ]
    Y_train_structured = np.array(
        Y_train_structured, dtype=[("status", "bool"), ("time", "<f8")]
    )

    Y_test_structured = [(Y_test.iloc[i], T_test.iloc[i]) for i in range(len(Y_test))]
    Y_test_structured = np.array(
        Y_test_structured, dtype=[("status", "bool"), ("time", "<f8")]
    )

    # brier_score expects survival scores
    return brier_score(
        Y_train_structured, Y_test_structured, 1 - Prediction, times=Time
    )[0]


def generate_score(metric: np.ndarray) -> Tuple[float, float]:
    percentile_val = 1.96
    return (np.mean(metric), percentile_val * np.std(metric) / np.sqrt(len(metric)))


def print_score(score: Tuple[float, float]) -> str:
    return str(round(score[0], 4)) + " +/- " + str(round(score[1], 4))
