
import numpy as np
import pandas as pd


def load_scg_data(file_path):
    """Load and inspect an ESP32/MPU6050 SCG recording."""

    df = pd.read_csv(file_path)

    print("Recording loaded successfully")
    print(f"Total samples: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    # Check missing values
    print("\nMissing values:")
    print(df.isnull().sum())

    # Check sample index continuity
    if "sample_index" in df.columns:
        differences = df["sample_index"].diff()

        dropped = df.index[differences > 1].tolist()

        if dropped:
            print(f"\nPossible dropped samples at rows: {dropped}")
        else:
            print("\nNo sample-index gaps detected.")

    # Convert raw MPU6050 readings to g
    for axis in ["ax", "ay", "az"]:
        if axis in df.columns:
            df[f"{axis}_g"] = df[axis] / 16384.0

    return df


def remove_gravity(df, axes=("ax_g", "ay_g", "az_g")):
    """Remove the static mean acceleration from each axis."""

    df = df.copy()

    for axis in axes:
        if axis in df.columns:
            df[f"{axis}_clean"] = df[axis] - df[axis].mean()

    return df
