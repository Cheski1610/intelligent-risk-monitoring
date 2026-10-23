from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def transactions() -> pd.DataFrame:
    size = 100
    rows = []
    for index in range(size):
        rows.append(
            {
                "step": index + 1,
                "type": ("PAYMENT", "TRANSFER", "CASH_OUT", "CASH_IN")[index % 4],
                "amount": 100.0 + (index % 17) * 13.5 + index * 0.3,
                "nameOrig": f"origin-{index // 2}",
                "oldbalanceOrg": 5000.0 + index * 30,
                "newbalanceOrig": 4900.0 + index * 25,
                "nameDest": f"destination-{index % 9}",
                "oldbalanceDest": 1000.0 + index * 10,
                "newbalanceDest": 1100.0 + index * 13,
                "isFraud": 1 if index in {5, 55, 88} else 0,
                "isFlaggedFraud": 0,
                "_source_row_id": str(index + 2),
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def paysim_csv(tmp_path, transactions):
    path = tmp_path / "transactions.csv"
    transactions.drop(columns=["_source_row_id"]).to_csv(path, index=False)
    return path
