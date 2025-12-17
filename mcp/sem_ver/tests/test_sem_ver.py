import unittest

import sem_ver
from sem_ver import (
    BumpPart,
    BumpVersionArgs,
    CompareOp,
    CompareVersionsArgs,
)


class TestSemVerTools(unittest.TestCase):
    def test_bump_patch(self) -> None:
        result = sem_ver.bump_version(
            BumpVersionArgs(version="1.2.5", part=BumpPart.patch, dry_run=True)
        )
        self.assertEqual(result["old"], "1.2.5")
        self.assertEqual(result["new"], "1.2.6")
        self.assertTrue(result["dryRun"])

    def test_bump_accepts_string_enum_part(self) -> None:
        result = sem_ver.bump_version(
            BumpVersionArgs(version="1.2.5", part="patch", dry_run=True)  # type: ignore[arg-type]
        )
        self.assertEqual(result["new"], "1.2.6")

    def test_bump_minor_resets_patch(self) -> None:
        result = sem_ver.bump_version(BumpVersionArgs(version="1.2.5", part=BumpPart.minor))
        self.assertEqual(result["new"], "1.3.0")

    def test_bump_major_resets_minor_patch(self) -> None:
        result = sem_ver.bump_version(BumpVersionArgs(version="1.2.5", part=BumpPart.major))
        self.assertEqual(result["new"], "2.0.0")

    def test_bump_clears_prerelease_and_build_by_default(self) -> None:
        result = sem_ver.bump_version(
            BumpVersionArgs(version="1.2.3-alpha.1+build.5", part=BumpPart.patch)
        )
        self.assertEqual(result["new"], "1.2.4")

    def test_bump_can_keep_prerelease_and_build(self) -> None:
        result = sem_ver.bump_version(
            BumpVersionArgs(
                version="1.2.3-alpha.1+build.5",
                part=BumpPart.patch,
                keep_prerelease=True,
            )
        )
        self.assertEqual(result["new"], "1.2.4-alpha.1+build.5")

    def test_compare_prerelease_lower_than_release(self) -> None:
        result = sem_ver.compare_versions(
            CompareVersionsArgs(
                left="1.0.0-alpha",
                right="1.0.0",
                op=CompareOp.lt,
            )
        )
        self.assertTrue(result["result"])

    def test_compare_accepts_string_enum_op(self) -> None:
        result = sem_ver.compare_versions(
            CompareVersionsArgs(left="1.0.0-alpha", right="1.0.0", op="lt")  # type: ignore[arg-type]
        )
        self.assertTrue(result["result"])

    def test_compare_build_metadata_ignored_for_precedence(self) -> None:
        result = sem_ver.compare_versions(
            CompareVersionsArgs(
                left="1.0.0+build.1",
                right="1.0.0+build.2",
                op=CompareOp.eq,
            )
        )
        self.assertTrue(result["result"])

    def test_compare_numeric_identifiers_lower_than_non_numeric(self) -> None:
        result = sem_ver.compare_versions(
            CompareVersionsArgs(
                left="1.0.0-alpha.1",
                right="1.0.0-alpha.beta",
                op=CompareOp.lt,
            )
        )
        self.assertTrue(result["result"])

    def test_compare_shorter_prerelease_has_lower_precedence(self) -> None:
        result = sem_ver.compare_versions(
            CompareVersionsArgs(
                left="1.0.0-alpha",
                right="1.0.0-alpha.1",
                op=CompareOp.lt,
            )
        )
        self.assertTrue(result["result"])

    def test_v_prefix_allowed(self) -> None:
        bumped = sem_ver.bump_version(BumpVersionArgs(version="v1.2.5", part=BumpPart.patch))
        self.assertEqual(bumped["new"], "1.2.6")

        compared = sem_ver.compare_versions(
            CompareVersionsArgs(left="v1.2.5", right="1.2.5", op=CompareOp.eq)
        )
        self.assertTrue(compared["result"])


if __name__ == "__main__":
    unittest.main()
