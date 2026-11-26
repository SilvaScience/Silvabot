"""
Recovers a Thorlabs CCS200 spectrometer that is stuck in "Firmware Loader" mode
(USB VID_1313/PID_8088) by pushing its Cypress EZ-USB firmware directly over
WinUSB via pyusb, bypassing TLCCSLoader64.sys.

Background: TLCCSLoader64.sys (Cypress "Generic USB Driver", 2010) is rejected by
Windows Code Integrity driver signing policy on some builds, so the CCS200 never
re-enumerates as the working device (PID_8089). That driver's only job is to push
the firmware described in CCS200.spt (a Cypress "CSPT" script file) via standard
EZ-USB anchor-download control transfers (bRequest 0xA0, the classic two-stage
"fxload" sequence). Once the firmware is pushed, the device re-enumerates as
PID_8089, which Windows binds via Thorlabs' own WinUSB-based VISA driver
(TLSPLICCODEVS_VIW7.inf) - already installed alongside NI-VISA/ThorSpectra, no
further changes needed for the existing ctypes/TLCCS_64.dll driver to work.

Prerequisite (one-time, per machine): the CCS200's PID_8088 interface must be
bound to WinUSB instead of TLCCSLoader64.sys (via Zadig - Options > List All
Devices > "Thorlabs CCS-Series Firmware Loader" > WinUSB > Replace Driver).
See: https://openproject.silvascience.org/projects/silvabot/wiki/thorlabs-ccs200-drivers
"""
import os
import struct
import time

VID = 0x1313
PID_LOADER = 0x8088
EZUSB_ANCHOR_DOWNLOAD = 0xA0

CSPT_MAGIC = b"CSPT"
CSPT_HEADER_FMT = "<4sLLLBBHLLL"  # magic, length, dummy8, dummy12, request, dummy17, addr, dummy20, dummy24, data_len
CSPT_HEADER_LEN = struct.calcsize(CSPT_HEADER_FMT)

DEFAULT_SPT_PATH = os.path.join(os.path.dirname(__file__), "dlls", "CCS200.spt")
_BUNDLED_LIBUSB_PATH = os.path.join(os.path.dirname(__file__), "dlls", "libusb-1.0.dll")


def _get_usb_backend():
    """pyusb needs a libusb-1.0 backend, which isn't always on PATH (e.g. when it
    only exists inside a conda env's Library/bin). Prefer the copy vendored
    alongside TLCCS_64.dll; fall back to pyusb's normal discovery otherwise."""
    import usb.backend.libusb1

    if os.path.exists(_BUNDLED_LIBUSB_PATH):
        backend = usb.backend.libusb1.get_backend(find_library=lambda x: _BUNDLED_LIBUSB_PATH)
        if backend is not None:
            return backend
    return usb.backend.libusb1.get_backend()


class _CsptChunk:
    __slots__ = ("request", "address", "data")

    def __init__(self, request, address, data):
        self.request = request
        self.address = address
        self.data = data


def _parse_cspt(path):
    """Parse a Cypress .spt script file into a flat list of CSPT chunks."""
    with open(path, "rb") as f:
        raw = f.read()

    chunks = []
    pos = 0
    while pos < len(raw):
        magic = raw[pos:pos + 4]
        if magic != CSPT_MAGIC:
            raise ValueError(f"Bad chunk magic at offset {pos}: {magic!r}")
        length = struct.unpack_from("<L", raw, pos + 4)[0]
        if length < 8:
            raise ValueError(f"Chunk length too small at offset {pos}: {length}")
        chunk_bytes = raw[pos:pos + length]
        if len(chunk_bytes) < length:
            raise EOFError("Truncated .spt file")

        (_magic, _length, _d8, _d12, request, _d17,
         addr, _d20, _d24, data_len) = struct.unpack_from(CSPT_HEADER_FMT, chunk_bytes, 0)
        data = chunk_bytes[CSPT_HEADER_LEN:CSPT_HEADER_LEN + data_len]
        if len(data) != data_len:
            raise ValueError(f"Data length mismatch at offset {pos}")

        chunks.append(_CsptChunk(request, addr, data))
        pos += length

    return chunks


def _extract_stages(chunks):
    """Group CSPT chunks into firmware upload stages, split on CPUCS reset-bit
    toggles (the standard two-stage EZ-USB boot sequence)."""
    stages = []
    current_stage = None
    cpucs_addr = None
    cpu_reset = 0

    for chunk in chunks:
        if chunk.request != EZUSB_ANCHOR_DOWNLOAD:
            continue

        if cpucs_addr is None:
            if len(chunk.data) != 1:
                raise ValueError("Expected first write to be a single byte to CPUCS")
            cpucs_addr = chunk.address

        if chunk.address == cpucs_addr:
            if len(chunk.data) != 1:
                raise ValueError("Unexpected multi-byte write to CPUCS")
            new_reset = chunk.data[0] & 1
            if new_reset == cpu_reset:
                continue
            if not cpu_reset:
                current_stage = []
                stages.append(current_stage)
            cpu_reset = new_reset
        else:
            if current_stage is None:
                raise ValueError("Firmware data write before CPUCS reset was asserted")
            current_stage.append((chunk.address, chunk.data))

    return stages, cpucs_addr


def _anchor_write(dev, address, data):
    # bmRequestType 0x40 = Host-to-device | Vendor | Device
    dev.ctrl_transfer(0x40, EZUSB_ANCHOR_DOWNLOAD, wValue=address, wIndex=0, data_or_wLength=data)


def _push_firmware(dev, cpucs_addr, stages):
    for stage in stages:
        _anchor_write(dev, cpucs_addr, bytes([1]))  # assert CPU reset
        for addr, data in stage:
            _anchor_write(dev, addr, data)
        _anchor_write(dev, cpucs_addr, bytes([0]))  # release CPU reset
        time.sleep(1.0)  # let the device reset/re-enumerate between stages


def ensure_ccs200_ready(spt_path=DEFAULT_SPT_PATH, timeout=5.0):
    """If a CCS200 is currently stuck in Firmware Loader mode (PID_8088), push its
    firmware over WinUSB so it re-enumerates as the working device (PID_8089).
    No-op if no such device is present (already initialized, not connected, or
    pyusb/libusb isn't available - in which case tlccs_init will fail with its
    usual error and the existing TLCCSLoader64.sys/driver-signing message applies).
    """
    try:
        import usb.core
        backend = _get_usb_backend()
    except ImportError:
        return

    dev = usb.core.find(idVendor=VID, idProduct=PID_LOADER, backend=backend)
    if dev is None:
        return

    print("ThorlabsCCS200: device found in Firmware Loader mode, pushing firmware...")
    chunks = _parse_cspt(spt_path)
    stages, cpucs_addr = _extract_stages(chunks)
    _push_firmware(dev, cpucs_addr, stages)

    deadline = time.time() + timeout
    while time.time() < deadline:
        if usb.core.find(idVendor=VID, idProduct=PID_LOADER, backend=backend) is None:
            break
        time.sleep(0.2)
    print("ThorlabsCCS200: firmware push complete.")
