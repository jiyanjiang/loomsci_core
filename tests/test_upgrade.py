from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import build_release  # noqa: E402
import upgrade  # noqa: E402


class UpgradeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        (self.home / "core").mkdir(parents=True)
        (self.home / "core" / "old.txt").write_text("old", encoding="utf-8")
        (self.home / "data").mkdir()
        (self.home / "data" / "data.db").write_bytes(b"db")
        self.out = Path(self.tmp.name) / "out"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _package(self):
        return Path(build_release.build(self.out)["archive"])

    def test_apply_preserves_data_and_rollback(self) -> None:
        package = self._package()
        result = upgrade.apply(package, self.home)
        self.assertTrue(result["ok"])
        self.assertTrue((self.home / "core" / "pyproject.toml").is_file())
        self.assertEqual((self.home / "data" / "data.db").read_bytes(), b"db")
        self.assertTrue((self.home / "core.prev" / "old.txt").is_file())
        restored = upgrade.rollback(self.home)
        self.assertTrue(restored["ok"])
        self.assertEqual((self.home / "core" / "old.txt").read_text(), "old")
        self.assertFalse((self.home / "data" / "data.db").read_bytes() != b"db")

    def test_signature_required_when_requested(self) -> None:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = Ed25519PrivateKey.generate()
        key_path = Path(self.tmp.name) / "key.raw"
        key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.Raw,
                serialization.PrivateFormat.Raw,
                serialization.NoEncryption(),
            )
        )
        package = Path(build_release.build(self.out, str(key_path))["archive"])
        sig = package.with_suffix(package.suffix + ".sig")
        pub = Path(self.tmp.name) / "pub.raw"
        pub.write_bytes(
            key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
        )
        upgrade.apply(package, self.home, signature=sig, public_key=pub)
        self.assertTrue((self.home / "core" / "pyproject.toml").is_file())

    def test_bad_signature_does_not_swap(self) -> None:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        package = self._package()
        key = Ed25519PrivateKey.generate()
        bad = Path(self.tmp.name) / "bad.sig"
        bad.write_bytes(key.sign(b"not the package"))
        pub = Path(self.tmp.name) / "pub.raw"
        pub.write_bytes(
            key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
        )
        with self.assertRaises(upgrade.UpgradeError):
            upgrade.apply(package, self.home, signature=bad, public_key=pub)
        self.assertTrue((self.home / "core" / "old.txt").is_file())
        self.assertFalse((self.home / "core" / "pyproject.toml").exists())


if __name__ == "__main__":
    unittest.main()
