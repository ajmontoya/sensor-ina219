#!/usr/bin/python3
import csv
import datetime
from pathlib import Path
import sys
import time

import click
from ina219 import DeviceRangeError, INA219


def get_test_filepath(output: str, testfile: str) -> Path:
    output: Path = Path(output)
    if not output.exists():
        output.mkdir()
    return Path(output / testfile)


def get_test_id(testpath: Path) -> int:
    if not testpath.exists():
        return 1
    else:
        with testpath.open(mode="r") as filereader:
            for line in filereader:
                pass
            last_row: str = line
            rid, *_ = last_row.split(",")
        return int(rid) + 1


def write_to_csv(csv_header: list[str], samples: list, testpath: Path) -> None:
    if not testpath.exists():
        with testpath.open(mode="w") as filewriter:
            csv_writer = csv.writer(filewriter, delimiter=",")
            csv_writer.writerow(csv_header)

    with testpath.open(mode="a") as fileappender:
        csv_appender = csv.writer(fileappender, delimiter=",")
        for sample in samples:
            csv_appender.writerow(sample)


def create_ina(i2c_address: int, shunt_ohms: float = 0.1, busnum: int = 1) -> INA219:
    ina: INA219 = INA219(shunt_ohms=shunt_ohms, busnum=busnum, address=i2c_address)
    ina.configure()
    ina.addr = i2c_address
    return ina


def create_ina_map(tests: tuple[tuple[str, str]]) -> dict[str, INA219]:
    return {test: create_ina(int(i2c_addr, 16)) for test, i2c_addr in tests}


def convert_to_datetime(ts: float) -> str:
    dt: datetime.datetime = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")


@click.command()
@click.option(
    "-f",
    "--filename",
    "filename",
    type=str,
    default="test",
    show_default=True,
    help="Name of csv file (default is 'test')",
)
@click.option(
    "-t",
    "--tests",
    "tests",
    type=(str, str),
    multiple=True,
    required=True,
    help="Map of test label to hex I2C address string (ex: -a test1 0x40)",
)
@click.option(
    "-v",
    "--verbose",
    "verbose",
    default=False,
    is_flag=True,
    show_default=True,
    help="Print to std out",
)
@click.option(
    "-o",
    "--output",
    "output",
    type=str,
    required=True,
    help="Output directory for test results",
)
def main(
    filename: str, tests: tuple[tuple[str, str]], verbose: bool, output: str
) -> None:
    ina_map: dict[str, INA219] = create_ina_map(tests)
    if verbose:
        print("TEST SENSORS => ", end=" ")
        for sensor_label, ina in ina_map.items():
            print(f"{sensor_label}: {hex(ina.addr)}", end=" ")
        print()

    samples: list = []

    testpath: Path = get_test_filepath(output, f"{filename}.csv")

    csv_header: list[str] = [
        "test id",
        "sensor label",
        "timestamp epoch sec",
        "timestamp datetime",
        "power mW",
        "supply voltage V",
        "current mA",
    ]

    try:
        i: int = get_test_id(testpath)

        if verbose:
            idx, sensor_label, ts, dt, power, voltage, current = csv_header
            print(
                f"{idx:>7}{sensor_label:>15}{ts:>24}{dt:>30}{power:>12}{voltage:>20}{current:>12}"
            )

        while True:
            for sensor_label, ina in ina_map.items():
                ts: float = time.time()
                dt: str = convert_to_datetime(ts)
                power: float = ina.power()
                supply_volt: float = ina.supply_voltage()
                current: float = ina.current()

                samples.append((i, sensor_label, ts, dt, power, supply_volt, current))

            if verbose:
                print(
                    f"{i:>7}{sensor_label:>15}{ts:>24}{dt:>30}{power:12.4f}{supply_volt:20.4f}{current:12.4f}"
                )

            i += 1
    except KeyboardInterrupt:
        print("User ended program run")
        print("Writing to csv file...please wait")
        write_to_csv(csv_header, samples, testpath)
        sys.exit(0)
    except DeviceRangeError as dev_err:
        print(f"Error in device's range: {dev_err}, program shutting down")
        sys.exit(1)


if __name__ == "__main__":
    main()
