#!/usr/bin/env python
#
# Complete logic for generating Bitcoin addresses from a wordlist scheme. All
# the code is contained within one file, so to run, simply ensure "click" is
# installed, and run using python:
#
#     pip install click
#     python airgap.py help
#
# Some commands require additional dependencies. See the help text for each
# subcommand.
#
# Should work with both Python 2 and Python 3.

import binascii
import csv
import hashlib

import click

try:
    from typing import List, Text, TextIO
except ImportError: pass

# Helpers
# =================
#
# Define some conversion helpers which work in both Python 2 and Python 3.
if hasattr(int, "from_bytes"):
    int_from_bytes = int.from_bytes
else:
    def int_from_bytes(data, byteorder, signed=False):
        assert byteorder == 'big'
        assert not signed

        return int(binascii.hexlify(data), 16)


if hasattr(int, "to_bytes"):
    def int_to_bytes(integer, length):
        return integer.to_bytes(length, byteorder='big')
else:
    def int_to_bytes(integer, length):
        hex_string = '%x' % integer
        return binascii.unhexlify(hex_string.zfill(length * 2))


if hasattr(bytes, "hex"):
    def bytes_to_hex(b):
        # type: (bytes) -> Text
        return b.hex()
else:
    def bytes_to_hex(b):
        # type: (bytes) -> Text
        return binascii.hexlify(b).decode('ascii')


if hasattr(bytes, "fromhex"):
    def bytes_from_hex(h):
        # type: (Text) -> bytes
        return bytes.fromhex(h)
else:
    def bytes_from_hex(h):
        # type: (Text) -> bytes
        return binascii.unhexlify(h)


# Crypto
# =================
#
# These are the actual meat of the code to derive secrets from the seed words
# and convert those secrets to bitcoin-relevant values. Each helper imports what
# it needs, so even if a system doesn't have all the dependencies, it can use
# the commands for which it does.
def seed_to_sk(seed, index):
    # type: (Text, int) -> int
    """Given the contents of a seed file, generate a secret key as an int."""
    phrase = b' '.join(word.encode('ascii') for word in seed.split())
    phrase += b' ' + str(index).encode('ascii') + b'\n'

    return int_from_bytes(hashlib.sha256(phrase).digest(), byteorder='big')


def sk_to_pk(sk):
    # type: (int) -> bytes
    """Converts private keys to public keys.

    The input is an integer as returned by seed_to_sk. The output is an
    uncompressed secp256k1 public key, as a byte string, as described in SEC 1
    v2.0 section 2.3.3.
    """
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat import backends
    priv_key = ec.derive_private_key(sk, ec.SECP256K1(), backends.default_backend())
    k = priv_key.public_key().public_numbers().encode_point()
    return k


def sk_to_wif(sk):
    # type: (int) -> Text
    """Converts a private key to WIF format.

    The input is an integer as returned by seed_to_sk. The output is an
    "uncompressed" WIF-format private key, ready to be added to your favorite
    bitcoin program.
    """
    from pycoin import key
    k = key.Key(secret_exponent=sk, netcode='BTC')
    return k.wif(use_uncompressed=True)


def pk_to_addr(pk):
    # type: (bytes) -> Text
    """Converts a public key to an uncompressed bitcoin address.

    The input is an uncompressed secp256k1 public key, as a byte string, as
    described in SEC 1 v2.0 section 2.3.3. The output is an uncompressed bitcoin
    address.
    """
    from pycoin import key
    return key.Key.from_sec(pk, netcode='BTC').address(use_uncompressed=True)

# Command line
# ============

@click.group()
def cli():
    pass


@cli.command()
@click.argument('seed_in', type=click.File('r'))
@click.argument('wif_out', type=click.File('w'))
@click.option('--start', default=0, help='First index for which to generate a WIF')
@click.option('--count', default=10, help='Number of WIFs to generate, starting from --start')
def wif(seed_in, wif_out, start, count):
    # type: (TextIO, TextIO, int, int) -> None
    """Gets WIFs from seed words.

    Generates --count private keys in uncompressed Wallet Import Format (WIF)
    for indices starting from --start. The output file is a two-column
    tab-separated value (TSV) file, with the first column being index and the
    second being the WIF for that index.

    Requires the "pycoin" library:

        pip install pycoin
    """
    seed = seed_in.read()
    tsv_out = tsv_writer(wif_out)
    for idx in range(start, start + count):
        wif = sk_to_wif(seed_to_sk(seed, idx))
        tsv_out.writerow([idx, wif])


@cli.command()
@click.argument('seed_in', type=click.File('r'))
@click.argument('pubkey_out', type=click.File('w'))
@click.option('--start', default=0,
              help='First index for which to generate a public key')
@click.option('--count', default=10,
              help='Number of public keys to generate, starting from --start')
def pubkey(seed_in, pubkey_out, start, count):
    # type: (TextIO, TextIO, int, int) -> None
    """Gets public keys from seed words.

    Generates --count public keys for indices starting from --start. The output
    file is a two-column tab-separated value (TSV) file, with the first column
    being the SEC1-formatted public key for that index.

    Requires the "cryptography" library:

        pip install cryptography
    """
    seed = seed_in.read()
    tsv_out = tsv_writer(pubkey_out)
    for idx in range(start, start + count):
        pubkey = sk_to_pk(seed_to_sk(seed, idx))
        tsv_out.writerow([idx, bytes_to_hex(pubkey)])


@cli.command()
@click.argument('pubkey_in', type=click.File('r'))
@click.argument('addr_out', type=click.File('w'))
def addr(pubkey_in, addr_out):
    # type: (TextIO, TextIO) -> None
    """Converts public keys to addresses.

    Input file should be a two-column tab-separated value (TSV) file, with the
    first column representing the index of a key, and the second being the
    SEC1-formatted public key for that index (see the output of the 'pubkey'
    subcommand). The output file is a two-column TSV file with matching indices
    in the first column, and corresponding uncompressed Bitcoin addresses in the
    second.

    Requires the "pycoin" library:

        pip install pycoin
    """
    tsv_out = tsv_writer(addr_out)
    for idx, pubkey_hex in tsv_reader(pubkey_in):
      pubkey = bytes_from_hex(pubkey_hex)
      tsv_out.writerow([idx, pk_to_addr(pubkey)])


def tsv_writer(outfile):
  return csv.writer(outfile, delimiter='\t', lineterminator='\n')


def tsv_reader(infile):
  return csv.reader(infile, delimiter='\t')


if __name__ == '__main__':
    cli()
