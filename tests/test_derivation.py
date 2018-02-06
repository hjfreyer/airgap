import binascii
import json
import os.path
import unittest

from typing import List, Dict, Any, Text
from parameterized import parameterized, param

from .context import airgap

TESTDATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def makeTestCases():
    with open(os.path.join(TESTDATA_DIR, 'vector.json')) as f:
        cases = json.load(f)
        for case in cases:
            for seed in case['seeds']:
                for addr in case['addrs']:
                    index = addr['index']
                    yield param('%s_%d' % (seed, index), seed, index, addr)


class TestStringMethods(unittest.TestCase):
    @parameterized.expand(makeTestCases)
    def test_all(self, _, seed, index, addr):
        # type: (Text, Text, int, Dict) -> None
        sk = airgap.seed_to_sk(seed, index)
        self.assertEqual(int(addr['sk'], 16), sk)

        wif = airgap.sk_to_wif(sk)
        self.assertEqual(addr['wif'], wif)

        pk = airgap.sk_to_pk(sk)
        self.assertEqual(binascii.unhexlify(addr['pk_sec']), pk)

        a = airgap.pk_to_addr(pk)
        self.assertEqual(addr['address'], a)


if __name__ == '__main__':
    unittest.main()
