import timeit
import gc
from asus_driver_extractor.core.inf_parser import InfParser

def benchmark():
    sample_inf = """
[Version]
Signature="$WINDOWS NT$"
Class=Net
ClassGUID={4d36e972-e325-11ce-bfc1-08002be10318}
Provider=%Realtek%
CatalogFile=rt68cx21x64.cat
DriverVer=07/17/2023,1168.015.0717.2023

[Manufacturer]
%Realtek% = Realtek, NTamd64.10.0

[Realtek.NTamd64.10.0]
%Realtek.DeviceDesc% = Realtek.ndi, PCI\\VEN_10EC&DEV_8168&SUBSYS_12341043
%Realtek.DeviceDesc2% = Realtek.ndi, USB\\VID_10EC&DEV_8168&SUBSYS_12341043
%Realtek.DeviceDesc3% = Realtek.ndi, ACPI\\VEN_10EC&DEV_8168&SUBSYS_12341043
%Realtek.DeviceDesc4% = Realtek.ndi, HDAUDIO\\VEN_10EC&DEV_8168&SUBSYS_12341043
%Realtek.DeviceDesc5% = Realtek.ndi, OTHER\\VEN_10EC&DEV_8168&SUBSYS_12341043
%Realtek.DeviceDesc6% = Realtek.ndi, PCI\\VEN_10EC&DEV_8169&SUBSYS_12341043

[SourceDisksFiles]
rt68cx21x64.sys = 1
rt68cx21x64.cat = 1

[Strings]
Realtek = "Realtek Semiconductor Corp."
Realtek.DeviceDesc = "Realtek Gaming GbE Family Controller"
""" * 100

    sections = InfParser._split_sections(sample_inf)
    strings = InfParser._parse_strings(sections.get("strings", []))

    def run():
        InfParser._parse_devices(sections, strings)

    # warm up
    run()

    gc.disable()
    timer = timeit.Timer(run)
    n, t = timer.autorange()
    gc.enable()

    print(f"Time per run: {t/n * 1e6:.2f} us")

if __name__ == "__main__":
    benchmark()
