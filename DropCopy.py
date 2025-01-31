import sys
import os
import shutil
import uuid
import time
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QGroupBox,
    QLabel,
    QPushButton,
    QListWidget,
    QMessageBox,
    QFileDialog,
    QProgressBar,
    QScrollArea,
    QMenu,
    QAction,
    QCheckBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QRunnable, QThreadPool
from PyQt5.QtGui import QIcon


def generate_suffix():
    """生成唯一后缀"""
    return uuid.uuid4().hex[:6]  # 使用UUID前6位，降低冲突概率


class DragDropLineEdit(QLineEdit):
    """支持拖放的路径输入框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.setText(path)
            else:
                QMessageBox.warning(self, "错误", "请拖放目录，而非文件！")
        event.acceptProposedAction()


class FileDropArea(QGroupBox):
    """文件拖放区域"""

    filesDropped = pyqtSignal(list)

    STYLE_NORMAL = """
        QGroupBox { 
            border: 2px dashed #aaa; 
            border-radius: 8px; 
            background-color: #f8f9fa; 
            margin-top: 1ex; 
            padding: 20px 0; 
        }
        QGroupBox::title { 
            subcontrol-origin: margin; 
            left: 12px; 
            padding: 0 6px; 
            color: #6c757d; 
        }
    """
    STYLE_ACTIVE = "QGroupBox { border: 2px dashed #0d6efd; background-color: #e7f1ff; }"

    def __init__(self, title):
        super().__init__(title)
        self.setAcceptDrops(True)
        self.setStyleSheet(self.STYLE_NORMAL)
        self.label = QLabel("拖放文件到这里")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #6c757d; font-size: 14px;")
        self.setMinimumSize(400, 150)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setStyleSheet(self.STYLE_ACTIVE)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.STYLE_NORMAL)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        valid_files = []
        invalid_files = []

        for url in urls:
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                valid_files.append(file_path)
            else:
                invalid_files.append(file_path)

        if valid_files:
            self.filesDropped.emit(valid_files)

        if invalid_files:
            QMessageBox.warning(self, "警告", f"{len(invalid_files)}个无效文件已忽略\n示例：{invalid_files[:3]}...")

        self.setStyleSheet(self.STYLE_NORMAL)
        event.acceptProposedAction()


class WorkerSignals(QObject):
    """工作线程信号"""

    progress_signal = pyqtSignal()
    error_signal = pyqtSignal(str)


class CopyWorker(QRunnable):
    """文件复制工作线程"""

    def __init__(self, src, dst):
        super().__init__()
        self.src = src
        self.dst = dst
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(self.dst), exist_ok=True)
            unique_dst = self.generate_unique_filename()
            shutil.copy2(self.src, unique_dst)
        except PermissionError as e:
            error_msg = f"无权限复制文件: {os.path.basename(self.src)} ({e})"
        except FileNotFoundError:
            error_msg = f"文件不存在: {os.path.basename(self.src)}"
        except Exception as e:
            error_msg = f"复制失败: {os.path.basename(self.src)} ({e})"
        else:
            error_msg = None
        finally:
            if error_msg:
                self.signals.error_signal.emit(error_msg)
            self.signals.progress_signal.emit()

    def generate_unique_filename(self):
        """生成唯一文件名"""
        base, ext = os.path.splitext(os.path.abspath(self.dst))  # 使用绝对路径
        for _ in range(1000):  # 增加尝试次数
            new_dst = f"{base}_{generate_suffix()}{ext}"
            if not os.path.exists(new_dst):
                return new_dst
        raise Exception("无法生成唯一文件名")


class DropZoneWidget(QWidget):
    """文件拖放区域控件"""
    deleted = pyqtSignal()  # 新增删除信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []
        layout = QVBoxLayout()

        self.drop_area = FileDropArea("拖放区域")
        self.drop_area.filesDropped.connect(self.handle_files_dropped)

        self.output_layout = QHBoxLayout()
        self.output_path = DragDropLineEdit()
        self.output_path.setPlaceholderText("选择输出目录...")
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setStyleSheet("QPushButton { padding: 5px 12px; }")
        self.browse_btn.clicked.connect(self.select_output_path)
        self.delete_btn = QPushButton("×")
        self.delete_btn.setStyleSheet(
            """
            QPushButton {
                padding: 5px 10px;
                color: #dc3545;
                border: 1px solid #dc3545;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #f8d7da;
            }
        """
        )
        self.delete_btn.clicked.connect(self.delete_self)

        self.select_files_btn = QPushButton("批量选择文件")
        self.select_files_btn.setStyleSheet("QPushButton { padding: 5px 12px; }")
        self.select_files_btn.clicked.connect(self.select_files)

        self.clear_files_btn = QPushButton("清空文件")
        self.clear_files_btn.setStyleSheet("QPushButton { padding: 5px 12px; }")
        self.clear_files_btn.clicked.connect(self.clear_files)

        self.sort_files_btn = QPushButton("按文件名排序")
        self.sort_files_btn.setStyleSheet("QPushButton { padding: 5px 12px; }")
        self.sort_files_btn.clicked.connect(self.sort_files)

        # 在DropZoneWidget的output_layout部分添加按钮
        self.import_btn = QPushButton("导入")
        self.export_btn = QPushButton("导出")
        self.import_btn.setStyleSheet("QPushButton { padding: 5px 12px; }")
        self.export_btn.setStyleSheet("QPushButton { padding: 5px 12px; }")

        # 将按钮添加到布局中（在原有按钮之后）
        self.output_layout.addWidget(self.import_btn)
        self.output_layout.addWidget(self.export_btn)

        # 连接按钮信号
        self.import_btn.clicked.connect(self.import_paths)
        self.export_btn.clicked.connect(self.export_paths)

        self.show_preview_checkbox = QCheckBox("显示文件预览")
        self.show_preview_checkbox.setChecked(False)
        self.show_preview_checkbox.setEnabled(False)
        self.show_preview_checkbox.stateChanged.connect(self.toggle_preview)

        self.output_layout.addWidget(self.output_path)
        self.output_layout.addWidget(self.browse_btn)
        self.output_layout.addWidget(self.delete_btn)
        self.output_layout.addWidget(self.select_files_btn)
        self.output_layout.addWidget(self.clear_files_btn)
        self.output_layout.addWidget(self.sort_files_btn)
        self.output_layout.addWidget(self.show_preview_checkbox)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)  # 启用扩展选择模式
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.show_context_menu)
        self.file_list.hide()

        layout.addWidget(self.drop_area)
        layout.addLayout(self.output_layout)
        layout.addWidget(self.file_list)
        self.setLayout(layout)

        self.output_path.textChanged.connect(self.update_drop_area_label)

    # 添加新的方法实现
    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() == Qt.Key_Delete:
            self.delete_selected_files()
        else:
            super().keyPressEvent(event)

    def delete_selected_files(self):
        """删除选中的多个文件"""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            return

        # 获取要删除的文件数量
        delete_count = len(selected_items)
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {delete_count} 个文件吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # 获取要删除的行号（逆序处理防止索引变化）
        rows = sorted([self.file_list.row(item) for item in selected_items], reverse=True)
        for row in rows:
            self.files.pop(row)
            self.file_list.takeItem(row)

        self.update_drop_area_label()
        if not self.files:
            self.show_preview_checkbox.setEnabled(False)


    def import_paths(self):
        """从文件导入路径"""
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择路径文件",
            "",
            "文本文件 (*.txt);;所有文件 (*)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                candidates = [line.strip() for line in f if line.strip()]
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"无法读取文件: {str(e)}")
            return

        valid_files = []
        invalid_files = []
        existing_files = set(self.files)

        for candidate in candidates:
            if not os.path.isfile(candidate):
                invalid_files.append(candidate)
                continue
            if candidate not in existing_files:
                valid_files.append(candidate)
                existing_files.add(candidate)

        if valid_files:
            self.files.extend(valid_files)
            self.file_list.addItems([os.path.basename(f) for f in valid_files])
            self.update_drop_area_label()
            self.show_preview_checkbox.setEnabled(True)

        report = []
        if valid_files:
            report.append(f"成功导入 {len(valid_files)} 个文件")
        if invalid_files:
            report.append(f"忽略 {len(invalid_files)} 个无效路径")
        
        if report:
            QMessageBox.information(
                self,
                "导入结果",
                "\n".join(report),
                QMessageBox.Ok
            )

    def export_paths(self):
        """导出路径到文件"""
        if not self.files:
            QMessageBox.warning(self, "警告", "当前区域没有可导出的文件路径")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存路径文件",
            f"文件路径_{time.strftime('%Y%m%d%H%M%S')}.txt",
            "文本文件 (*.txt);;所有文件 (*)"
        )
        if not path:
            return

        # 获取当前输出路径
        output_dir = self.output_path.text().strip()

        try:
            with open(path, "w", encoding="utf-8") as f:
                # 写入输出路径作为第一行
                f.write(output_dir + "\n")
                # 写入文件路径
                f.write("\n".join(self.files))
            QMessageBox.information(
                self,
                "导出成功",
                f"路径已保存到:\n{path}",
                QMessageBox.Ok
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "导出失败",
                f"保存文件时出错:\n{str(e)}",
                QMessageBox.Ok
            )

    def import_paths(self):
        """从文件导入路径"""
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择路径文件",
            "",
            "文本文件 (*.txt);;所有文件 (*)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"无法读取文件: {str(e)}")
            return

        if not lines:
            QMessageBox.warning(self, "导入失败", "文件为空")
            return

        # 第一行是输出路径候选
        output_dir_candidate = lines[0]
        file_candidates = lines[1:] if len(lines) > 1 else []

        # 询问用户是否应用该输出路径
        reply = QMessageBox.question(
            self,
            "导入输出路径",
            f"导出文件中包含的输出路径为：{output_dir_candidate}\n是否应用此路径到当前区域？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            self.output_path.setText(output_dir_candidate)

        # 处理文件路径
        valid_files = []
        invalid_files = []
        existing_files = set(self.files)

        for candidate in file_candidates:
            if not os.path.isfile(candidate):
                invalid_files.append(candidate)
                continue
            if candidate not in existing_files:
                valid_files.append(candidate)
                existing_files.add(candidate)

        if valid_files:
            self.files.extend(valid_files)
            self.file_list.addItems([os.path.basename(f) for f in valid_files])
            self.update_drop_area_label()
            self.show_preview_checkbox.setEnabled(True)

        report = []
        if reply == QMessageBox.Yes:
            report.append(f"已应用输出路径：{output_dir_candidate}")
        if valid_files:
            report.append(f"成功导入 {len(valid_files)} 个文件")
        if invalid_files:
            report.append(f"忽略 {len(invalid_files)} 个无效路径")
        
        if report:
            QMessageBox.information(
                self,
                "导入结果",
                "\n".join(report),
                QMessageBox.Ok
            )

    def update_drop_area_label(self):
        """更新拖放区域标签"""
        output_path = self.output_path.text()
        file_count = len(self.files)

        path_info = f"输出到：{output_path}" if output_path else "⚠️ 未设置输出目录"
        count_info = f"已选择 {file_count} 个文件" if file_count > 0 else "拖放文件到这里"

        self.drop_area.label.setText(f"{path_info}\n{count_info}")

    def handle_files_dropped(self, new_files):
        """处理拖放文件"""
        existing = set(self.files)
        added = [f for f in new_files if f not in existing]
        if not added:
            QMessageBox.information(self, "提示", "没有新增文件（已过滤重复项）")
            return

        self.files.extend(added)
        self.update_drop_area_label()
        for file in added:
            self.file_list.addItem(os.path.basename(file))
        if added:
            self.show_preview_checkbox.setEnabled(True)

    def select_output_path(self):
        """选择输出目录"""
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.output_path.setText(path)
            self.update_drop_area_label()

    def delete_self(self):
        """删除当前区域"""
        if (
            QMessageBox.question(
                self,
                "确认删除",
                "确定要删除此区域吗？已选择的文件将丢失！",
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            self.setParent(None)
            self.deleteLater()
            self.deleted.emit()  # 发射删除信号

    def select_files(self):
        """批量选择文件"""
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件")
        if files:
            self.handle_files_dropped(files)

    def clear_files(self):
        """清空文件列表"""
        self.files = []
        self.file_list.clear()
        self.show_preview_checkbox.setChecked(False)  # 强制取消选中
        self.show_preview_checkbox.setEnabled(False)
        self.update_drop_area_label()
        self.file_list.hide()  # 确保隐藏列表

    def sort_files(self):
        """按文件名排序"""
        self.files.sort()
        self.file_list.clear()
        for file in self.files:
            self.file_list.addItem(os.path.basename(file))

    def show_context_menu(self, pos):
        """显示右键菜单（支持多选操作）"""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            return

        menu = QMenu(self)
        
        # 删除操作（支持多选）
        delete_action = QAction(f"删除选中项（{len(selected_items)}个）", self)
        delete_action.triggered.connect(self.delete_selected_files)
        menu.addAction(delete_action)

        # 复制路径操作（仅单选时可用）
        if len(selected_items) == 1:
            copy_action = QAction("复制路径", self)
            copy_action.triggered.connect(lambda: self.copy_file_path(self.file_list.row(selected_items[0])))
            menu.addAction(copy_action)

        # 批量导出操作
        export_action = QAction("导出选中路径" if len(selected_items) > 1 else "导出所有路径", self)
        export_action.triggered.connect(lambda: self.export_selected_paths(selected_items))
        menu.addAction(export_action)

        menu.exec_(self.file_list.mapToGlobal(pos))

    def export_selected_paths(self, selected_items):
        """导出选中路径"""
        selected_files = [self.files[self.file_list.row(item)] for item in selected_items]
        
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存路径文件",
            f"文件路径_{time.strftime('%Y%m%d%H%M%S')}.txt",
            "文本文件 (*.txt);;所有文件 (*)"
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(selected_files))
            QMessageBox.information(
                self,
                "导出成功",
                f"成功导出 {len(selected_files)} 条路径！",
                QMessageBox.Ok
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "导出失败",
                f"保存文件时出错：\n{str(e)}",
                QMessageBox.Ok
            )

    def delete_file(self, row):
        """删除指定文件"""
        file = self.files.pop(row)
        self.file_list.takeItem(row)
        self.update_drop_area_label()
        if not self.files:
            self.show_preview_checkbox.setEnabled(False)

    def copy_file_path(self, row):
        """复制文件路径"""
        file = self.files[row]
        clipboard = QApplication.clipboard()
        clipboard.setText(file)

    def toggle_preview(self, state):
        """切换文件预览"""
        if state == Qt.Checked:
            self.file_list.show()
        else:
            self.file_list.hide()


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件复制中转站")
        self.setGeometry(100, 100, 1000, 600)
        self.drop_zones = []
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f8f9fa;
            }
            QPushButton {
                background-color: #e9ecef;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #dee2e6;
            }
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px;
            }
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0d6efd;
                border-radius: 3px;
            }
        """
        )

        icon_path = "app.ico"
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.setWindowIcon(icon)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        self.layout = QVBoxLayout()

        self.control_layout = QHBoxLayout()
        self.add_zone_btn = QPushButton("➕ 添加区域")
        self.copy_btn = QPushButton("🚀 开始复制")
        self.control_layout.addWidget(self.add_zone_btn)
        self.control_layout.addStretch()
        self.control_layout.addWidget(self.copy_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)

        self.layout.addLayout(self.control_layout)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.scroll_area)
        self.main_widget.setLayout(self.layout)

        self.add_zone_btn.clicked.connect(self.add_drop_zone)
        self.copy_btn.clicked.connect(self.start_copy)
        self.thread_pool = QThreadPool.globalInstance()

        self.drop_zones = []
        self.add_drop_zone()
        self.errors = []
        self.tasks = []

    def add_drop_zone(self):
        """添加拖放区域"""
        zone = DropZoneWidget()
        self.drop_zones.append(zone)
        self.scroll_layout.addWidget(zone)
        zone.deleted.connect(lambda: self.remove_drop_zone(zone))  # 连接信号

    def remove_drop_zone(self, zone):
        """处理区域删除"""
        if zone in self.drop_zones:
            self.drop_zones.remove(zone)  # 从列表中移除
        zone.deleteLater()  # 确保控件被销毁

    def start_copy(self):
        """开始复制文件"""
        if not self.validate_paths():
            return

        self.tasks = []
        for zone in self.drop_zones:
            output_path = zone.output_path.text().strip()
            if output_path and zone.files:
                for src in zone.files:
                    if os.path.isfile(src):
                        dst = os.path.join(output_path, os.path.basename(src))
                        self.tasks.append((src, dst))

        if not self.tasks:
            QMessageBox.warning(self, "警告", "没有需要复制的文件！")
            return

        self.total_files = len(self.tasks)
        self.completed_files = 0
        self.errors = []
        self.start_time = time.time()
        self.progress_bar.setValue(0)
        self.copy_btn.setEnabled(False)
        self.add_zone_btn.setEnabled(False)

        self.max_threads = min(self.thread_pool.maxThreadCount(), os.cpu_count() * 2)
        self.running_tasks = 0
        self._schedule_tasks()

    def _schedule_tasks(self):
        """调度任务到线程池"""
        while self.running_tasks < self.max_threads and self.tasks:
            src, dst = self.tasks.pop(0)
            worker = CopyWorker(src, dst)
            worker.signals.progress_signal.connect(self.update_progress)
            worker.signals.error_signal.connect(self.show_error)
            self.thread_pool.start(worker)
            self.running_tasks += 1

    def update_progress(self):
        """更新进度条"""
        self.completed_files += 1
        self.running_tasks -= 1
        progress = int((self.completed_files / self.total_files) * 100)
        self.progress_bar.setValue(progress)

        elapsed = time.time() - self.start_time
        if elapsed > 0:
            speed = self.completed_files / elapsed
            remaining = (self.total_files - self.completed_files) / speed
            time_str = f"{int(remaining // 60):02d}:{int(remaining % 60):02d}"
            self.progress_bar.setFormat(
                f"进度: {progress}% - 剩余时间: {time_str} - 速度: {speed:.1f} 文件/秒"
            )

        self._schedule_tasks()

        if self.completed_files == self.total_files:
            self.copy_btn.setEnabled(True)
            self.add_zone_btn.setEnabled(True)
            self.progress_bar.setFormat("复制完成！")

            for zone in self.drop_zones:
                zone.files = []
                zone.file_list.clear()
                zone.update_drop_area_label()
                zone.show_preview_checkbox.setEnabled(False)

            msg = []
            if self.errors:
                success = self.total_files - len(self.errors)
                msg.append(f"✅ 成功复制: {success} 文件")
                msg.append(f"❌ 失败: {len(self.errors)} 文件")
                msg.append("\n错误详情：\n" + "\n".join(self.errors[:5]))
                if len(self.errors) > 5:
                    msg.append(f"...及其他 {len(self.errors)-5} 个错误")
                QMessageBox.critical(self, "复制结果", "\n".join(msg))
            else:
                QMessageBox.information(self, "完成", f"✅ 成功复制 {self.total_files} 个文件！")

    def validate_paths(self):
        """验证输出路径"""
        invalid_zones = []
        for idx, zone in enumerate(self.drop_zones, 1):
            path = zone.output_path.text().strip()
            if not path:
                invalid_zones.append(str(idx))
                continue

            try:
                os.makedirs(path, exist_ok=True)
                if not os.path.isdir(path):
                    invalid_zones.append(str(idx))
                    QMessageBox.critical(self, "错误", f"路径不是目录: {path}")
                    continue

                # 验证写权限
                test_file = os.path.join(path, ".write_test")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
            except PermissionError:
                invalid_zones.append(str(idx))
                QMessageBox.critical(self, "错误", f"目录无写权限: {path}")
            except Exception as e:
                invalid_zones.append(str(idx))
                QMessageBox.critical(self, "错误", f"无法创建目录 {path}：{str(e)}")

        if invalid_zones:
            QMessageBox.warning(
                self,
                "路径错误",
                f"以下区域存在问题：{', '.join(invalid_zones)}\n"
                "请确保所有区域都设置了有效的输出目录",
            )
            return False
        return True

    def show_error(self, error_msg):
        """显示错误信息"""
        self.errors.append(error_msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())