
from .context import airgap


from typing import List, Dict, Any, Text
import unittest
from hypothesis import given, assume
import hypothesis
import os.path
import hypothesis.strategies as st
from parameterized import parameterized, param
import json
import os

import binascii
import glob
import sys
import subprocess
import tempfile
import shutil

#from builtins import bytes

SCRIPT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'airgap.py')
TESTDATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def makeTestCaseDirs():
    for case in glob.glob(TESTDATA_DIR + '/files/*'):
        yield case
        #        yield os.path.join(TESTDATA_DIR, case)

def makeWifTestCases():
    for case_dir in makeTestCaseDirs():
        params = json.load(open(os.path.join(case_dir, 'params.json')))
        for seed in glob.glob(case_dir + '/seeds/*.txt'):
            yield param(seed,
                        os.path.join(case_dir, 'wif.tsv'),
                        params)

def makePubkeyOutTestCases():
    for case_dir in makeTestCaseDirs():
        params = json.load(open(os.path.join(case_dir, 'params.json')))
        for seed in glob.glob(case_dir + '/seeds/*.txt'):
            yield param(seed,
                        os.path.join(case_dir, 'pubkey.tsv'),
                        params)

def makePubkeyToAddrTestCases():
    for case_dir in makeTestCaseDirs():
        yield param(os.path.join(case_dir, 'pubkey.tsv'),
                    os.path.join(case_dir, 'addr.tsv'))



class TestStringMethods(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def call_it(self, args):
        subprocess.check_call([sys.executable, SCRIPT_FILE] + args)

    @parameterized.expand(makeWifTestCases)
    def test_wif(self, seed_path, expected_wif_path, params):
        # type: (Text, Text, Dict) -> None
        actual_wif_path = os.path.join(self.tmp_dir, 'wif.out.tsv')
        self.call_it(['wif', seed_path, actual_wif_path,
                      '--start', str(params['start']),
                      '--count', str(params['count'])])
        with open(expected_wif_path, 'r') as f:
            expected_wif = f.read()
        with open(actual_wif_path, 'r') as f:
            actual_wif = f.read()

        self.assertEqual(expected_wif, actual_wif)

    @parameterized.expand(makePubkeyOutTestCases)
    def test_pubkey(self, seed_path, expected_pubkey_path, params):
        # type: (Text, Text, Dict) -> None
        actual_pubkey_path = os.path.join(self.tmp_dir, 'pubkey.out.tsv')
        self.call_it(['pubkey', seed_path, actual_pubkey_path,
                      '--start', str(params['start']),
                      '--count', str(params['count'])])
        with open(expected_pubkey_path) as f:
            expected_pubkey = f.read()
        with open(actual_pubkey_path) as f:
            actual_pubkey = f.read()

        self.assertEqual(expected_pubkey, actual_pubkey)

    @parameterized.expand(makePubkeyToAddrTestCases)
    def test_addr(self, pubkey_path, expected_addr_path):
        # type: (Text, Text) -> None
        actual_addr_path = os.path.join(self.tmp_dir, 'addr.out.tsv')
        self.call_it(['addr', pubkey_path, actual_addr_path])
        with open(expected_addr_path) as f:
            expected_addr = f.read()
        with open(actual_addr_path) as f:
            actual_addr = f.read()

        self.assertEqual(expected_addr, actual_addr)

if __name__ == '__main__':
    unittest.main()
