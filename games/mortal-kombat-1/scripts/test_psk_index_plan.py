"""Synthetic fixtures only; no game/model payloads."""
import struct
import tempfile
import unittest
from pathlib import Path
from psk_index_plan import create_plan, read_psk
from mk1_checks import patch_indices


def section(name, size, count, payload):
    return struct.pack('<20s3i', name, 0, size, count) + payload


def psk_bytes(indices, wide=False, vertices=4):
    fmt, stride, name = ('<3I', 18, b'FACE3200') if wide else ('<3H', 12, b'FACE0000')
    payload = b''.join(struct.pack(fmt, *indices[i:i+3]) + bytes(6) for i in range(0, len(indices), 3))
    return (section(b'ACTRHEAD', 0, 0, b'') + section(b'VTXW0000', 16, vertices, bytes(vertices*16))
            + section(name, stride, len(indices)//3, payload))


class PlanTests(unittest.TestCase):
    def test_full_reversed_duplicate_and_patch(self):
        with tempfile.TemporaryDirectory() as temp:
            psk, raw, out = [Path(temp)/n for n in ('mesh.psk', 'raw', 'hidden')]
            psk.write_bytes(psk_bytes([0, 1, 2, 2, 3, 0]))
            payload = struct.pack('<6H', 1, 0, 2, 3, 2, 0)
            buffer = bytes([2]) + struct.pack('<II', 2, 6) + payload
            raw.write_bytes(b'KEEP' + buffer + b'KEEP' + buffer + b'KEEP')
            plan = create_plan(raw, [psk])
            self.assertEqual(len(plan['buffers']), 2)
            self.assertEqual(plan['buffers'][0]['evidence'][0]['permutation'], [1, 0, 2])
            self.assertEqual(patch_indices(raw, out, plan)['triangles_collapsed'], 4)
            self.assertTrue(out.read_bytes().endswith(b'KEEP'))

    def test_prefix_match_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            psk, raw = Path(temp)/'mesh.psk', Path(temp)/'raw'
            values = [0, 1, 2] * 40
            psk.write_bytes(psk_bytes(values))
            values[-1] = 3  # first 96 indices still identical
            raw.write_bytes(bytes([2]) + struct.pack('<II', 2, len(values)) + struct.pack('<120H', *values))
            with self.assertRaises(ValueError):
                create_plan(raw, [psk])

    def test_uint32_stream(self):
        with tempfile.TemporaryDirectory() as temp:
            psk, raw = Path(temp)/'mesh.psk', Path(temp)/'raw'
            psk.write_bytes(psk_bytes([0, 1, 70000], wide=True, vertices=70001))
            raw.write_bytes(bytes([4]) + struct.pack('<II3I', 4, 3, 0, 1, 70000))
            self.assertEqual(create_plan(raw, [psk])['buffers'][0]['width'], 4)

    def test_invalid_psk_and_missing_lod_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            psk, second, raw = [Path(temp)/n for n in ('a.psk', 'b.psk', 'raw')]
            psk.write_bytes(psk_bytes([0, 1, 4]))
            with self.assertRaises(ValueError):
                read_psk(psk)
            psk.write_bytes(psk_bytes([0, 1, 2])[:-1])
            with self.assertRaises(ValueError):
                read_psk(psk)
            psk.write_bytes(psk_bytes([0, 1, 2]))
            second.write_bytes(psk_bytes([0, 1, 3]))
            raw.write_bytes(bytes([2]) + struct.pack('<II3H', 2, 3, 0, 1, 2))
            with self.assertRaises(ValueError):
                create_plan(raw, [psk, second])


if __name__ == '__main__':
    unittest.main()
