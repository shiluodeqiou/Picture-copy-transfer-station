import unittest
from unittest.mock import patch, MagicMock
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
import os
import string
import shutil
from DropCopy import generate_suffix, CopyWorker, DropZoneWidget, MainWindow


class TestFileCopyApp(unittest.TestCase):

    def setUp(self):
        self.app = QApplication(sys.argv)
        self.window = MainWindow()

    def tearDown(self):
        for zone in self.window.drop_zones:
            zone.deleteLater()
        self.window.close()
        self.app.quit()
        # 显式删除对象引用，帮助垃圾回收
        del self.window
        del self.app

    def test_generate_suffix(self):
        suffix = generate_suffix()
        self.assertEqual(len(suffix), 6)
        self.assertTrue(all(c in string.ascii_letters + string.digits for c in suffix))

    def test_CopyWorker_generate_unique_filename(self):
        src = "test_src.txt"
        dst = "test_dst.txt"
        worker = CopyWorker(src, dst)
        unique_dst = worker.generate_unique_filename()
        self.assertEqual(os.path.dirname(unique_dst), os.path.dirname(dst))

    def test_DropZoneWidget_handle_files_dropped(self):
        zone = DropZoneWidget()
        new_files = ["file1.txt", "file2.txt"]
        with patch.object(QMessageBox, 'information') as mock_info:
            zone.handle_files_dropped(new_files)
            self.assertEqual(len(zone.files), 2)
            mock_info.assert_not_called()

        # 测试重复文件过滤
        with patch.object(QMessageBox, 'information') as mock_info:
            zone.handle_files_dropped(new_files)
            self.assertEqual(len(zone.files), 2)
            mock_info.assert_called_once()

    def test_MainWindow_validate_paths(self):
        zone = DropZoneWidget()
        self.window.drop_zones = [zone]

        # 测试无路径情况
        zone.output_path.setText("")
        with patch.object(QMessageBox, 'warning') as mock_warning:
            result = self.window.validate_paths()
            self.assertFalse(result)
            mock_warning.assert_called()

        # 测试有效路径情况
        valid_path = os.getcwd()
        zone.output_path.setText(valid_path)
        with patch.object(QMessageBox, 'warning') as mock_warning:
            result = self.window.validate_paths()
            self.assertTrue(result)
            mock_warning.assert_not_called()

    def test_DropZoneWidget_clear_files(self):
        zone = DropZoneWidget()
        new_files = ["file1.txt", "file2.txt"]
        zone.handle_files_dropped(new_files)
        self.assertEqual(len(zone.files), 2)

        zone.clear_files()
        self.assertEqual(len(zone.files), 0)
        self.assertEqual(zone.file_list.count(), 0)
        self.assertFalse(zone.show_preview_checkbox.isEnabled())

    def test_DropZoneWidget_sort_files(self):
        zone = DropZoneWidget()
        new_files = ["c.txt", "a.txt", "b.txt"]
        zone.handle_files_dropped(new_files)
        zone.sort_files()
        sorted_files = [zone.files[i] for i in range(len(zone.files))]
        self.assertEqual(sorted_files, sorted(new_files))

    def test_DropZoneWidget_delete_file(self):
        zone = DropZoneWidget()
        new_files = ["file1.txt", "file2.txt", "file3.txt"]
        zone.handle_files_dropped(new_files)
        initial_count = len(zone.files)

        zone.delete_file(1)
        self.assertEqual(len(zone.files), initial_count - 1)
        self.assertEqual(zone.file_list.count(), initial_count - 1)

    def test_DropZoneWidget_toggle_preview(self):
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
        print("预览开关状态变为选中，文件列表是否可见: ", zone.file_list.isVisible())
        self.assertTrue(zone.file_list.isVisible())

        # 测试取消选中时隐藏文件列表
        zone.show_preview_checkbox.setChecked(False)
        QApplication.processEvents()
        print("预览开关状态变为取消选中，文件列表是否可见: ", zone.file_list.isVisible())
        self.assertFalse(zone.file_list.isVisible())

    def test_MainWindow_add_drop_zone(self):
        initial_zone_count = len(self.window.drop_zones)
        self.window.add_drop_zone()
        self.assertEqual(len(self.window.drop_zones), initial_zone_count + 1)

    def test_file_copy_functionality(self):
        # 创建测试源文件
        test_src = "test_source_file.txt"
        with open(test_src, 'w') as f:
            f.write("Test content")

        # 创建测试目标目录
        test_dst_dir = "test_destination_dir"
        os.makedirs(test_dst_dir, exist_ok=True)
        test_dst = os.path.join(test_dst_dir, os.path.basename(test_src))

        # 创建 CopyWorker 实例
        worker = CopyWorker(test_src, test_dst)

        # 模拟信号连接
        progress_mock = MagicMock()
        error_mock = MagicMock()
        worker.signals.progress_signal.connect(progress_mock)
        worker.signals.error_signal.connect(error_mock)

        print(f"源文件: {test_src}")
        print(f"目标文件: {test_dst}")

        # 运行复制任务
        try:
            worker.run()
            print("文件复制成功完成。")
        except Exception as e:
            print(f"文件复制失败: {e}")
            self.fail(f"文件复制失败: {e}")

        # 检查文件是否复制成功
        self.assertTrue(os.path.exists(test_dst))
        # 检查信号是否按预期发射
        progress_mock.assert_called_once()
        error_mock.assert_not_called()

        # 清理测试文件和目录
        os.remove(test_src)
        shutil.rmtree(test_dst_dir)


if __name__ == "__main__":
    unittest.main()