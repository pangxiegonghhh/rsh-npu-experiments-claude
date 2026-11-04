import csv
import json
import tempfile
import unittest
from pathlib import Path

from rsh_reorder_experiment import (
    SparseMatrix,
    _validate_native_permutation,
    inverse_permutation,
    run_experiment,
    synthetic_matrix,
    window_metrics,
    write_outputs,
    write_batch_outputs,
)


class RSHReorderExperimentTests(unittest.TestCase):
    def setUp(self):
        self.matrix = SparseMatrix.from_rows(
            [
                [(0, 1), (1, 2)],
                [(0, 3), (1, 4)],
                [(4, 5), (5, 6)],
                [(4, 7), (5, 8)],
                [(1, 9), (2, 10)],
                [(2, 11), (3, 12)],
                [],
            ],
            n_cols=6,
            name="tiny",
        )

    def test_all_methods_return_reversible_semantic_outputs(self):
        result = run_experiment(self.matrix, w16=4, k=3, neutron_cluster_windows=2)
        self.assertEqual(len(result["outputs"]), 8)
        for output in result["outputs"]:
            self.assertTrue(all(output["correctness"].values()), output)
            self.assertEqual(sorted(output["row_perm"]), list(range(self.matrix.n_rows)))
            self.assertEqual(sorted(output["inverse_row_perm"]), list(range(self.matrix.n_rows)))
            self.assertEqual(output["matrix_nnz"], self.matrix.nnz)

    def test_same_fixed_configuration_is_deterministic(self):
        first = run_experiment(self.matrix, w16=4, k=3, seed=17, neutron_cluster_windows=2)
        second = run_experiment(self.matrix, w16=4, k=3, seed=17, neutron_cluster_windows=2)
        first_orders = {(item["method"], item["view"]): item["row_perm"] for item in first["outputs"]}
        second_orders = {(item["method"], item["view"]): item["row_perm"] for item in second["outputs"]}
        self.assertEqual(first_orders, second_orders)
        first_cols = {(item["method"], item["view"]): item["optional_col_perm"] for item in first["outputs"]}
        second_cols = {(item["method"], item["view"]): item["optional_col_perm"] for item in second["outputs"]}
        self.assertEqual(first_cols, second_cols)

    def test_window_metrics_use_fixed_w16_and_k16(self):
        order = list(range(self.matrix.n_rows))
        windows, summary = window_metrics(order, self.matrix.supports, w16=4, n_cols=self.matrix.n_cols)
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0]["row_count"], 4)
        self.assertEqual(windows[0]["unique_columns"], 4)
        self.assertEqual(windows[0]["k16_count"], 1)
        self.assertEqual(summary["window_count"], 2)
        wide = SparseMatrix.from_rows([range(20), range(20)], n_cols=20, name="wide")
        wide_windows, _ = window_metrics([0, 1], wide.supports, w16=2, n_cols=20)
        self.assertEqual(wide_windows[0]["k16_count"], 2)  # K16 remains 16 even when W16 is 2

    def test_native_column_permutation_preserves_semantics(self):
        row_perm = [2, 0, 1, 3, 4, 5, 6]
        col_perm = [2, 0, 5, 1, 4, 3]
        self.assertTrue(_validate_native_permutation(self.matrix, row_perm, col_perm))
        inverse = inverse_permutation(row_perm)
        self.assertEqual([inverse[row] for row in row_perm], list(range(self.matrix.n_rows)))

    def test_small_nonzero_is_preserved(self):
        matrix = SparseMatrix.from_rows([[(0, 1e-13)]], n_cols=1)
        self.assertEqual(matrix.entries, (((0, 1e-13),),))

    def test_occupancy_uses_k_width(self):
        matrix = SparseMatrix.from_rows([range(20), range(20)], n_cols=20)
        windows, _ = window_metrics([0, 1], matrix.supports, w16=2, n_cols=20)
        self.assertEqual(windows[0]["occupancy"], 0.625)

    def test_long_spanning_tree_dfs_is_iterative(self):
        from rsh_reorder_experiment import _maximum_spanning_dfs
        size = 1500
        graph = {i: {} for i in range(size)}
        for i in range(size - 1):
            graph[i][i + 1] = graph[i + 1][i] = 1.0
        self.assertEqual(_maximum_spanning_dfs(list(range(size)), graph), list(range(size)))

    def test_output_files_include_required_artifacts(self):
        result = run_experiment(self.matrix, w16=4, k=3, neutron_cluster_windows=2)
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(write_outputs(result, tmp))
            self.assertTrue((output_dir / "manifest.json").exists())
            self.assertTrue((output_dir / "method_metrics.csv").exists())
            self.assertTrue((output_dir / "window_metrics.csv").exists())
            self.assertTrue((output_dir / "row_order_structure_comparison.svg").exists())
            self.assertTrue((output_dir / "W16_window_nonzero_union.svg").exists())
            self.assertTrue((output_dir / "continuous_run_distribution.svg").exists())
            json_files = list(output_dir.glob("tiny__*.json"))
            self.assertEqual(len(json_files), 8)
            with (output_dir / "method_metrics.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 8)
            payload = json.loads((output_dir / "tiny__rsh__row_only.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["optional_col_perm"], None)
            self.assertEqual(payload["method"], "rsh")

    def test_batch_outputs_include_method_by_matrix_tables(self):
        first = run_experiment(self.matrix, w16=4, k=3, neutron_cluster_windows=2)
        second_matrix = SparseMatrix.from_rows([[0, 2], [2, 3], [5]], n_cols=6, name="tiny_second")
        second = run_experiment(second_matrix, w16=4, k=3, neutron_cluster_windows=2)
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(write_batch_outputs([first, second], tmp))
            self.assertTrue((output_dir / "tiny" / "tiny__rsh__row_only.json").exists())
            self.assertTrue((output_dir / "tiny_second" / "tiny_second__rsh__row_only.json").exists())
            with (output_dir / "method_metrics.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 16)
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["matrix_count"], 2)

    def test_synthetic_fixture_has_expected_shape(self):
        matrix = synthetic_matrix(32, 48, seed=9)
        self.assertEqual((matrix.n_rows, matrix.n_cols), (32, 48))
        self.assertGreater(matrix.nnz, 0)
        result = run_experiment(matrix, w16=8)
        self.assertTrue(all(all(item["correctness"].values()) for item in result["outputs"]))


if __name__ == "__main__":
    unittest.main()

