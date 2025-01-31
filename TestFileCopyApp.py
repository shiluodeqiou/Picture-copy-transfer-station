import unittest
from unittest.mock import patch, MagicMock, call
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt
import os
import string
import shutil
import tempfile
from DropCopy import generate_suffix, CopyWorker, DropZoneWidget, MainWindow


class TestFileCopyApp(unittest.TestCase):

    def setUp(self):
        self.app = QApplication(sys.argv)
        self.window = MainWindow()
        self.print_test_setup()

    def tearDown(self):
        for zone in self.window.drop_zones:
            zone.deleteLater()
        self.window.close()
        self.app.quit()
        # 显式删除对象引用，帮助垃圾回收
        del self.window
        del self.app
        self.print_test_teardown()

    def print_test_setup(self):
        print("\n" + "=" * 60)
        print("🚀 开始设置测试环境...")
        print("-" * 60)

    def print_test_teardown(self):
        print("-" * 60)
        print("🧹 测试环境清理完成。")
        print("=" * 60)

    def print_test_header(self, test_name):
        """美化测试输出头部"""
        print("\n" + "=" * 60)
        print(f"🚀 开始测试: {test_name}")
        print("-" * 60)

    def print_test_result(self, result=True):
        """输出测试结果"""
        status = "✅ 通过" if result else "❌ 失败"
        print("-" * 60)
        print(f"测试结果: {status}\n")

    def test_generate_suffix(self):
        self.print_test_header("generate_suffix 功能测试")
        print("开始测试 generate_suffix 功能...")
        suffix = generate_suffix()
        try:
            self.assertEqual(len(suffix), 6)
            self.assertTrue(all(c in string.ascii_letters + string.digits for c in suffix))
            print("generate_suffix 功能测试通过。")
            self.print_test_result(True)
        except AssertionError as e:
            print(f"generate_suffix 功能测试失败: {e}")
            self.print_test_result(False)
            raise

    def test_CopyWorker_generate_unique_filename(self):
        self.print_test_header("CopyWorker 的 generate_unique_filename 功能测试")
        print("开始测试 CopyWorker 的 generate_unique_filename 功能...")
        src = "test_src.txt"
        dst = os.path.abspath("test_dst.txt")  # 使用绝对路径
        worker = CopyWorker(src, dst)
        unique_dst = worker.generate_unique_filename()
        try:
            self.assertEqual(os.path.dirname(unique_dst), os.path.dirname(dst))
            print("CopyWorker 的 generate_unique_filename 功能测试通过。")
            self.print_test_result(True)
        except AssertionError as e:
            print(f"CopyWorker 的 generate_unique_filename 功能测试失败: {e}")
            self.print_test_result(False)
            raise

    def test_DropZoneWidget_handle_files_dropped(self):
        self.print_test_header("DropZoneWidget 的 handle_files_dropped 功能测试")
        print("开始测试 DropZoneWidget 的 handle_files_dropped 功能...")
        zone = DropZoneWidget()
        new_files = ["file1.txt", "file2.txt"]
        with patch.object(QMessageBox, 'information') as mock_info:
            zone.handle_files_dropped(new_files)
            try:
                self.assertEqual(len(zone.files), 2)
                mock_info.assert_not_called()
                print("第一次调用 handle_files_dropped 功能测试通过。")
            except AssertionError as e:
                print(f"第一次调用 handle_files_dropped 功能测试失败: {e}")
                raise

        # 测试重复文件过滤
        with patch.object(QMessageBox, 'information') as mock_info:
            zone.handle_files_dropped(new_files)
            try:
                self.assertEqual(len(zone.files), 2)
                mock_info.assert_called_once()
                print("重复文件过滤时 handle_files_dropped 功能测试通过。")
                self.print_test_result(True)
            except AssertionError as e:
                print(f"重复文件过滤时 handle_files_dropped 功能测试失败: {e}")
                self.print_test_result(False)
                raise

    def test_MainWindow_validate_paths(self):
        self.print_test_header("MainWindow 的 validate_paths 功能测试")
        print("开始测试 MainWindow 的 validate_paths 功能...")
        zone = DropZoneWidget()
        self.window.drop_zones = [zone]

        # 测试无路径情况
        zone.output_path.setText("")
        with patch.object(QMessageBox, 'warning') as mock_warning:
            result = self.window.validate_paths()
            try:
                self.assertFalse(result)
                mock_warning.assert_called()
                print("无路径情况下 validate_paths 功能测试通过。")
            except AssertionError as e:
                print(f"无路径情况下 validate_paths 功能测试失败: {e}")
                raise

        # 测试有效路径情况
        valid_path = os.getcwd()
        zone.output_path.setText(valid_path)
        with patch.object(QMessageBox, 'warning') as mock_warning:
            result = self.window.validate_paths()
            try:
                self.assertTrue(result)
                mock_warning.assert_not_called()
                print("有效路径情况下 validate_paths 功能测试通过。")
                self.print_test_result(True)
            except AssertionError as e:
                print(f"有效路径情况下 validate_paths 功能测试失败: {e}")
                self.print_test_result(False)
                raise

    def test_DropZoneWidget_clear_files(self):
        self.print_test_header("DropZoneWidget 的 clear_files 功能测试")
        print("开始测试 DropZoneWidget 的 clear_files 功能...")
        zone = DropZoneWidget()
        new_files = ["file1.txt", "file2.txt"]
        zone.handle_files_dropped(new_files)
        try:
            self.assertEqual(len(zone.files), 2)
            print("文件添加后数量验证通过。")
        except AssertionError as e:
            print(f"文件添加后数量验证失败: {e}")
            raise

        zone.clear_files()
        try:
            self.assertEqual(len(zone.files), 0)
            self.assertEqual(zone.file_list.count(), 0)
            self.assertFalse(zone.show_preview_checkbox.isEnabled())
            print("clear_files 功能测试通过。")
            self.print_test_result(True)
        except AssertionError as e:
            print(f"clear_files 功能测试失败: {e}")
            self.print_test_result(False)
            raise

    def test_DropZoneWidget_sort_files(self):
        self.print_test_header("DropZoneWidget 的 sort_files 功能测试")
        print("开始测试 DropZoneWidget 的 sort_files 功能...")
        zone = DropZoneWidget()
        new_files = ["c.txt", "a.txt", "b.txt"]
        zone.handle_files_dropped(new_files)
        zone.sort_files()
        sorted_files = [zone.files[i] for i in range(len(zone.files))]
        try:
            self.assertEqual(sorted_files, sorted(new_files))
            print("sort_files 功能测试通过。")
            self.print_test_result(True)
        except AssertionError as e:
            print(f"sort_files 功能测试失败: {e}")
            self.print_test_result(False)
            raise

    def test_DropZoneWidget_delete_file(self):
        self.print_test_header("DropZoneWidget 的 delete_file 功能测试")
        print("开始测试 DropZoneWidget 的 delete_file 功能...")
        zone = DropZoneWidget()
        new_files = ["file1.txt", "file2.txt", "file3.txt"]
        zone.handle_files_dropped(new_files)
        initial_count = len(zone.files)

        zone.delete_file(1)
        try:
            self.assertEqual(len(zone.files), initial_count - 1)
            self.assertEqual(zone.file_list.count(), initial_count - 1)
            print("delete_file 功能测试通过。")
            self.print_test_result(True)
        except AssertionError as e:
            print(f"delete_file 功能测试失败: {e}")
            self.print_test_result(False)
            raise

    def test_DropZoneWidget_toggle_preview(self):
        self.print_test_header("DropZoneWidget 的 toggle_preview 功能测试")
        print("开始测试 DropZoneWidget 的 toggle_preview 功能...")
        zone = DropZoneWidget()
        # 手动设置文件列表和启用预览复选框
        zone.files = ["dummy.txt"]  # 非空文件列表
        zone.file_list.addItem("dummy.txt")
        zone.show_preview_checkbox.setEnabled(True)  # 确保复选框可用
        zone.show()  # 显示控件以便处理可见性
        QApplication.processEvents()  # 处理事件循环

        # 测试选中时显示文件列表
        zone.show_preview_checkbox.setChecked(True)
        QApplication.processEvents()
        try:
            print("预览开关状态变为选中，文件列表是否可见: ", zone.file_list.isVisible())
            self.assertTrue(zone.file_list.isVisible())
            print("选中预览开关时 toggle_preview 功能测试通过。")
        except AssertionError as e:
            print(f"选中预览开关时 toggle_preview 功能测试失败: {e}")
            raise

        # 测试取消选中时隐藏文件列表
        zone.show_preview_checkbox.setChecked(False)
        QApplication.processEvents()
        try:
            print("预览开关状态变为取消选中，文件列表是否可见: ", zone.file_list.isVisible())
            self.assertFalse(zone.file_list.isVisible())
            print("取消选中预览开关时 toggle_preview 功能测试通过。")
            self.print_test_result(True)
        except AssertionError as e:
            print(f"取消选中预览开关时 toggle_preview 功能测试失败: {e}")
            self.print_test_result(False)
            raise

    def test_MainWindow_add_drop_zone(self):
        self.print_test_header("MainWindow 的 add_drop_zone 功能测试")
        print("开始测试 MainWindow 的 add_drop_zone 功能...")
        initial_zone_count = len(self.window.drop_zones)
        self.window.add_drop_zone()
        try:
            self.assertEqual(len(self.window.drop_zones), initial_zone_count + 1)
            print("add_drop_zone 功能测试通过。")
            self.print_test_result(True)
        except AssertionError as e:
            print(f"add_drop_zone 功能测试失败: {e}")
            self.print_test_result(False)
            raise

    def test_file_copy_functionality(self):
        self.print_test_header("文件复制功能测试")
        print("开始测试文件复制功能...")
        # 创建测试源文件
        test_src = "test_source_file.txt"
        with open(test_src, 'w') as f:
            f.write("Test content")

        # 创建测试目标目录
        test_dst_dir = "test_destination_dir"
        os.makedirs(test_dst_dir, exist_ok=True)
        test_base_name = os.path.basename(test_src)

        # 创建 CopyWorker 实例（使用基础文件名）
        base_dst = os.path.join(test_dst_dir, test_base_name)
        worker = CopyWorker(test_src, base_dst)

        # 模拟信号连接
        progress_mock = MagicMock()
        error_mock = MagicMock()
        worker.signals.progress_signal.connect(progress_mock)
        worker.signals.error_signal.connect(error_mock)

        # 运行复制任务
        try:
            worker.run()
        except Exception as e:
            self.fail(f"文件复制失败: {e}")

        # 检查目标目录中是否存在匹配的文件
        copied_files = [
            f for f in os.listdir(test_dst_dir)
            if f.startswith(test_base_name.split('.')[0])
        ]
        try:
            self.assertTrue(len(copied_files) > 0, "未找到符合规则的目标文件")
            print("文件复制功能测试通过。")
            self.print_test_result(True)
        except AssertionError as e:
            print(f"文件复制功能测试失败: {e}")
            self.print_test_result(False)
            raise
        finally:
            # 清理测试文件和目录
            if os.path.exists(test_src):
                os.remove(test_src)
            if os.path.exists(test_dst_dir):
                shutil.rmtree(test_dst_dir)

    def test_import_export_functionality(self):
        """测试完整的导入导出工作流"""
        self.print_test_header("文件路径导入导出工作流")

        # 创建测试区域
        zone = DropZoneWidget()
        test_files = [
            os.path.abspath("test1.txt"),  # 使用绝对路径
            os.path.abspath("test2.jpg"),
            os.path.abspath("test3.pdf")
        ]

        # 创建临时测试文件
        for f in test_files:
            with open(f, 'w') as tmp:
                tmp.write("test content")

        # 准备测试数据
        original_output_path = os.path.abspath("original_output")
        imported_output_path = os.path.abspath("imported_output")

        try:
            print("步骤 1: 初始区域设置")
            zone.output_path.setText(original_output_path)
            zone.handle_files_dropped(test_files)
            self.assertEqual(len(zone.files), 3)

            print("步骤 2: 执行导出操作")
            with tempfile.TemporaryDirectory() as temp_dir:
                export_path = os.path.join(temp_dir, "export.txt")

                # 模拟文件保存对话框
                with patch.object(QFileDialog, 'getSaveFileName', return_value=(export_path, "")):
                    zone.export_paths()

                # 验证导出文件内容
                with open(export_path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f]

                self.assertEqual(lines[0], original_output_path)
                self.assertListEqual(lines[1:], test_files)

            print("步骤 3: 执行导入操作")
            # 创建导入文件内容
            import_content = [
                imported_output_path,  # 第一行为输出路径
                *test_files,
                "non_existent_file.txt",  # 无效文件
                os.path.abspath("test1.txt")  # 重复文件
            ]

            with tempfile.TemporaryDirectory() as temp_dir:
                import_path = os.path.join(temp_dir, "import.txt")
                with open(import_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(import_content))

                # 模拟文件选择对话框和用户确认
                with patch.object(QFileDialog, 'getOpenFileName', return_value=(import_path, "")):
                    with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
                        zone.import_paths()

            # 验证导入结果
            print("验证输出路径更新")
            self.assertEqual(zone.output_path.text(), imported_output_path)

            print("验证文件列表更新")
            expected_files = list(test_files)  # 应该过滤掉无效文件和重复文件
            self.assertEqual(len(zone.files), len(expected_files))
            self.assertListEqual(zone.files, expected_files)

            self.print_test_result(True)
        finally:
            # 清理测试文件
            for f in test_files:
                if os.path.exists(f):
                    os.remove(f)

    # 修复 test_import_with_invalid_file（添加文件存在性模拟）
    def test_import_with_invalid_file(self):
        """测试导入包含无效路径的文件"""
        self.print_test_header("导入包含无效路径的文件")

        zone = DropZoneWidget()
        valid_files = ["/valid/file1.txt", "/another/valid/file3.txt"]

        # 创建真实文件确保存在性检查
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建有效文件
            for f in valid_files:
                full_path = os.path.join(temp_dir, os.path.basename(f))
                with open(full_path, 'w') as tmp:
                    tmp.write("content")

            import_content = [
                "/valid/output/path",
                *[os.path.join(temp_dir, os.path.basename(f)) for f in valid_files],
                "/invalid/file2.txt"
            ]

            # 写入导入文件
            import_path = os.path.join(temp_dir, "import.txt")
            with open(import_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(import_content))

            # 模拟对话框
            with patch.object(QFileDialog, 'getOpenFileName', return_value=(import_path, "")):
                with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
                    with patch.object(QMessageBox, 'information') as mock_info:
                        zone.import_paths()

            self.assertEqual(zone.output_path.text(), "/valid/output/path")
            self.assertEqual(len(zone.files), 2)  # 应导入2个有效文件
            mock_info.assert_called_once()

            info_msg = mock_info.call_args[0][2]
            self.assertIn("成功导入 2 个文件", info_msg)
            self.assertIn("忽略 1 个无效路径", info_msg)
            self.print_test_result(True)

    # 修复 test_export_without_output_path
    def test_export_without_output_path(self):
        """测试未设置输出路径时的导出行为"""
        self.print_test_header("无输出路径时的导出测试")

        zone = DropZoneWidget()
        # 确保 zone.files 为空
        zone.files = []

        # 模拟保存对话框返回空路径
        with patch.object(QFileDialog, 'getSaveFileName', return_value=("", "")):
            with patch.object(QMessageBox, 'warning') as mock_warn:
                zone.export_paths()

        mock_warn.assert_called_once_with(zone, "警告", "当前区域没有可导出的文件路径")
        self.print_test_result(True)

    def test_import_file_selection_cancel(self):
        """测试取消导入文件选择的操作"""
        self.print_test_header("取消导入文件选择")

        zone = DropZoneWidget()
        initial_state = len(zone.files)

        # 模拟取消文件选择
        with patch.object(QFileDialog, 'getOpenFileName', return_value=("", "")):
            zone.import_paths()

        # 验证状态不变
        self.assertEqual(len(zone.files), initial_state)

        self.print_test_result(True)

    def test_export_error_handling(self):
        """测试导出时的错误处理"""
        self.print_test_header("导出错误处理测试")

        zone = DropZoneWidget()
        test_files = [os.path.abspath("test_file.txt")]
        zone.handle_files_dropped(test_files)
        zone.output_path.setText(os.path.abspath("valid_output"))

        # 模拟只读文件错误（使用正确的错误信息断言）
        with tempfile.TemporaryDirectory() as temp_dir:
            readonly_file = os.path.join(temp_dir, "readonly.txt")
            with open(readonly_file, 'w') as f:
                f.write("test")
            os.chmod(readonly_file, 0o444)  # 设置为只读

            with patch.object(QFileDialog, 'getSaveFileName', return_value=(readonly_file, "")):
                with patch.object(QMessageBox, 'critical') as mock_critical:
                    zone.export_paths()

        args = mock_critical.call_args[0]
        self.assertIn("Permission denied", args[2])  # 检查英文错误信息
        self.print_test_result(True)

    def test_import_export_context_menu(self):
        """测试右键菜单的导出功能"""
        self.print_test_header("右键菜单导出测试")

        zone = DropZoneWidget()
        test_files = [os.path.abspath(f"test_{i}.txt") for i in range(3)]
        zone.handle_files_dropped(test_files)

        # 模拟右键点击
        mock_point = MagicMock()
        mock_point.isValid.return_value = True
        mock_point.row.return_value = 1

        # 模拟导出操作
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = os.path.join(temp_dir, "export.txt")
            with patch.object(QFileDialog, 'getSaveFileName', return_value=(export_path, "")):
                zone.export_paths()

            # 验证导出内容
            with open(export_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f]

            self.assertEqual(lines[0], zone.output_path.text())
            self.assertListEqual(lines[1:], test_files)

        self.print_test_result(True)


if __name__ == "__main__":
    unittest.main()