import timeit
from asus_driver_extractor.core.inf_parser import InfParser

def run_benchmark():
    # Construct a dummy sections dict to simulate a large INF file
    sections = {}
    for i in range(1000):
        sections[f"mfg_{i}"] = [
            f"Device{j} = %DeviceDesc{j}%, PCI\\VEN_10EC&DEV_8168" for j in range(10)
        ]
        sections[f"other_{i}"] = [
            f"SomeLine = SomeValue" for j in range(10)
        ]

    strings = {
        f"devicedesc{j}": f"My Device {j}" for j in range(10)
    }

    def bench_target():
        InfParser._parse_devices(sections, strings)

    # warm up
    bench_target()

    # time it
    times = timeit.repeat(bench_target, number=10, repeat=5)
    print(f"Baseline times (10 runs, 5 repeats): {times}")
    print(f"Min time: {min(times):.4f} seconds")

if __name__ == "__main__":
    run_benchmark()
