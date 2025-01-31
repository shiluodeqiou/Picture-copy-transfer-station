import sys
import os
import shutil
import random
import string
import time
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


def generate_suffix():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


class FileDropArea(QGroupBox):
    filesDropped = pyqtSignal(list)

    def __init__(self, title):
        super().__init__(title)
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QGroupBox {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f8f9fa;
                margin-top: 1ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #6c757d;
            }
        """)
        self.setMinimumSize(400, 150)

        layout = QVBoxLayout()
        self.label = QLabel("拖放文件到这里")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #6c757d; font-size: 14px;")
        layout.addWidget(self.label)
        self.setLayout(layout)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setStyleSheet("QGroupBox { border: 2px dashed #0d6efd; background-color: #e7f1ff; }")
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QGroupBox {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f8f9fa;
            }
        """)

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
            QMessageBox.warning(self, "警告",
                                f"{len(invalid_files)}个无效文件已忽略\n示例：{invalid_files[:3]}...")

        self.setStyleSheet("""
            QGroupBox {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f8f9fa;
            }
        """)
        event.acceptProposedAction()


class WorkerSignals(QObject):
    progress_signal = pyqtSignal()
    error_signal = pyqtSignal(str)


class CopyWorker(QRunnable):
    def __init__(self, src, dst):
        super().__init__()
        self.src = src
        self.dst = dst
        self.signals = WorkerSignals()

    def run(self):
        try:
            unique_dst = self.generate_unique_filename()
            shutil.copy2(self.src, unique_dst)
        except Exception as e:
            self.signals.error_signal.emit(f"错误复制 {os.path.basename(self.src)}: {str(e)}")
        finally:
            self.signals.progress_signal.emit()

    def generate_unique_filename(self):
        if not os.path.exists(self.dst):
            return self.dst

        counter = 1
        base, ext = os.path.splitext(self.dst)
        while True:
            new_dst = f"{base}_{generate_suffix()}{ext}"
            if not os.path.exists(new_dst):
                return new_dst
            counter += 1
            if counter > 100:
                raise Exception("无法生成唯一文件名")


class DropZoneWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []
        layout = QVBoxLayout()

        self.drop_area = FileDropArea("拖放区域")
        self.drop_area.filesDropped.connect(self.handle_files_dropped)

        self.output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("选择输出目录...")
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setStyleSheet("QPushButton { padding: 5px 12px; }")
        self.browse_btn.clicked.connect(self.select_output_path)
        self.delete_btn = QPushButton("×")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                color: #dc3545;
                border: 1px solid #dc3545;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #f8d7da;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_self)

        self.output_layout.addWidget(self.output_path)
        self.output_layout.addWidget(self.browse_btn)
        self.output_layout.addWidget(self.delete_btn)

        layout.addWidget(self.drop_area)
        layout.addLayout(self.output_layout)
        self.setLayout(layout)

    def handle_files_dropped(self, new_files):
        existing = set(self.files)
        added = [f for f in new_files if f not in existing]
        if not added:
            QMessageBox.information(self, "提示", "没有新增文件（已过滤重复项）")
            return

        self.files.extend(added)
        self.drop_area.label.setText(f"已选择 {len(self.files)} 个文件")

    def select_output_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.output_path.setText(path)

    def delete_self(self):
        if QMessageBox.question(
                self, "确认删除",
                "确定要删除此区域吗？已选择的文件将丢失！",
                QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self.setParent(None)
            self.deleteLater()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件复制工具")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("""
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
        """)

        # 加载图标文件
        icon_path = "app.ico"
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.setWindowIcon(icon)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        self.layout = QVBoxLayout()
        self.drop_zones = []

        # 控制按钮
        self.control_layout = QHBoxLayout()
        self.add_zone_btn = QPushButton("➕ 添加区域")
        self.copy_btn = QPushButton("🚀 开始复制")
        self.control_layout.addWidget(self.add_zone_btn)
        self.control_layout.addStretch()
        self.control_layout.addWidget(self.copy_btn)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.layout.addLayout(self.control_layout)
        self.layout.addWidget(self.progress_bar)
        self.main_widget.setLayout(self.layout)

        # 信号连接
        self.add_zone_btn.clicked.connect(self.add_drop_zone)
        self.copy_btn.clicked.connect(self.start_copy)
        self.thread_pool = QThreadPool.globalInstance()

        # 初始化
        self.add_drop_zone()
        self.errors = []
        self.tasks = []

    def add_drop_zone(self):
        zone = DropZoneWidget()
        self.drop_zones.append(zone)
        self.layout.insertWidget(len(self.drop_zones), zone)

    def start_copy(self):
        if not self.validate_paths():
            return

        # 收集所有任务
        self.tasks = []
        for zone in self.drop_zones:
            if zone.output_path.text() and zone.files:
                output_path = zone.output_path.text()
                os.makedirs(output_path, exist_ok=True)

                for src in zone.files:
                    if os.path.isfile(src):
                        dst = os.path.join(output_path, os.path.basename(src))
                        self.tasks.append((src, dst))

        if not self.tasks:
            QMessageBox.warning(self, "警告", "没有需要复制的文件！")
            return

        # 初始化复制状态
        self.total_files = len(self.tasks)
        self.completed_files = 0
        self.errors = []
        self.start_time = time.time()
        self.progress_bar.setValue(0)
        self.copy_btn.setEnabled(False)
        self.add_zone_btn.setEnabled(False)

        # 启动线程池
        self.max_threads = min(self.thread_pool.maxThreadCount(), 8)
        self.running_tasks = 0
        self._schedule_tasks()

    def _schedule_tasks(self):
        while self.running_tasks < self.max_threads and self.tasks:
            src, dst = self.tasks.pop(0)
            worker = CopyWorker(src, dst)
            worker.signals.progress_signal.connect(self.update_progress)
            worker.signals.error_signal.connect(self.show_error)
            self.thread_pool.start(worker)
            self.running_tasks += 1

    def update_progress(self):
        self.completed_files += 1
        self.running_tasks -= 1
        progress = int((self.completed_files / self.total_files) * 100)
        self.progress_bar.setValue(progress)

        # 更新进度信息
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            speed = self.completed_files / elapsed
            remaining = (self.total_files - self.completed_files) / speed
            time_str = f"{int(remaining // 60):02d}:{int(remaining % 60):02d}"
            self.progress_bar.setFormat(
                f"进度: {progress}% - 剩余时间: {time_str} - 速度: {speed:.1f} 文件/秒"
            )

        # 继续调度任务
        self._schedule_tasks()

        # 完成处理
        if self.completed_files == self.total_files:
            self.copy_btn.setEnabled(True)
            self.add_zone_btn.setEnabled(True)
            self.progress_bar.setFormat("复制完成！")

            # 清空文件但保留路径
            for zone in self.drop_zones:
                zone.files = []
                zone.drop_area.label.setText("拖放文件到这里")

            # 显示汇总信息
            msg = []
            if self.errors:
                msg.append(f"成功复制: {self.total_files - len(self.errors)} 文件")
                msg.append(f"失败: {len(self.errors)} 文件")
                msg.append("\n错误详情：\n" + "\n".join(self.errors[:5]))
                if len(self.errors) > 5:
                    msg.append(f"...及其他 {len(self.errors) - 5} 个错误")
                QMessageBox.critical(self, "复制结果", "\n".join(msg))
            else:
                QMessageBox.information(self, "完成", f"成功复制 {self.total_files} 个文件！")

    def validate_paths(self):
        invalid_zones = []
        for idx, zone in enumerate(self.drop_zones, 1):
            path = zone.output_path.text()
            if not path.strip():
                invalid_zones.append(str(idx))
            elif not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"无法创建目录 {path}：{str(e)}")
                    return False
        if invalid_zones:
            QMessageBox.warning(self, "警告", f"区域 {', '.join(invalid_zones)} 的输出路径未设置！")
            return False
        return True

    def show_error(self, error_msg):
        self.errors.append(error_msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())